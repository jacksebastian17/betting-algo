from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from html.parser import HTMLParser
import pprint
import copy
import pybettor as pb
import pandas as pd
import os
import threading


XPATH = "xpath"
CLASS_NAME = "class name"
BANKROLL = 32.83
KELLY = 1

class Parser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        global start_tags
        start_tags.append(tag)
        for a in attrs:
            all_attrs.append(a)
    def handle_data(self, data):
        global all_dataW
        all_data.append(data)
start_tags = []
all_attrs = []
all_data = []

options = Options()
options.headless = True
options.add_argument('--log-level=3')


bovada_sports = [
    {"league" : "NBA", "link" : 'https://www.bovada.lv/sports/basketball/nba'},
    {"league" : "NFL", "link" : 'https://www.bovada.lv/sports/football/nfl'},
    {"league" : "NHL", "link" : 'https://www.bovada.lv/sports/hockey/nhl'},
    {"league" : "NCAAMB", "link" : 'https://www.bovada.lv/sports/basketball/college-basketball'},
    {"league" : "NCAAF", "link" : 'https://www.bovada.lv/sports/football/college-football/ncaaf'},
    {"league" : "World Cup", "link" : 'https://www.bovada.lv/sports/soccer/fifa-world-cup'}
]
pinnacle_sports = [
    {"league" : "NBA", "link" : 'https://www.pinnacle.com/en/basketball/nba/matchups#period:0'},
    {"league" : "NFL", "link" : 'https://www.pinnacle.com/en/football/nfl/matchups#period:0'},
    {"league" : "NHL", "link" : 'https://www.pinnacle.com/en/hockey/nhl/matchups#period:0'},
    {"league" : "NCAAMB", "link" : 'https://www.pinnacle.com/en/basketball/ncaa/matchups#period:0'},
    {"league" : "NCAAF", "link" : 'https://www.pinnacle.com/en/football/ncaa/matchups#period:0'},
    {"league" : "World Cup", "link" : 'https://www.pinnacle.com/en/soccer/fifa-world-cup/matchups#period:0'}
]

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def name_converter(team):
    team = team.replace("L.A.", "Los Angeles")
    return team

def bovada_scraper(thread, entry):
    global bovada_games
    driver = webdriver.Chrome(options=options)
    driver.get(entry['link'])
    driver.implicitly_wait(5)

    elements = driver.find_elements(By.CLASS_NAME, 'game-view-cta')
    links = []
    try:
        links = [i for i in [elem.get_attribute('href') for elem in elements] if i is not None]
    except:
        print("   Failed on retrieving href links")
    parser = Parser()

    responses = []
    for link in links:
        driver.get(link)
        print(thread, "scraping Bovada link:", link)

        game = driver.find_element(By.CLASS_NAME, 'h2-heading')
        parser.feed(game.get_attribute('innerHTML'))

        # get teams playing
        teams = []
        for d in all_data:
            if d == '@' or d == 'vs':
                continue
            teams.append(d[1:-1])
        team1 = teams[0].replace(u'\xa0', '')
        team2 = teams[1].replace(u'\xa0', '')
        # remove ranking from any ranked teams in their name (i.e. Tennessee (+7) => Tennessee)
        if '(' in team1:
            team1 = team1[:team1.index('(') - 1]
        if '(' in team2:
            team2 = team2[:team2.index('(') - 1]
        team1 = name_converter(team1)
        team2 = name_converter(team2)

        response = {"team1" : team1, "team2" : team2}

        all_data.clear()

        # get all the betting markets for this game
        markets = driver.find_elements(By.CLASS_NAME, 'coupon-container')

        markets_json_array = []
        alternate_spread_flag = False
        alternate_totals_flag = False
        for i in range(len(markets)):
            try:
                html = markets[i].get_attribute('innerHTML')
            except:
                print("   Failed on retrieving innerHTML from markets[i]")
            parser.feed(html)
            if ('class', 'market-type suspended') in all_attrs:
                all_data.clear()
                all_attrs.clear()
                continue

            # convert EVEN -> +100
            for j, item in enumerate(all_data):
                if item == ' EVEN ':
                    all_data[j] = ' +100 '
                if item == ' (EVEN) ':
                    all_data[j] = ' (+100) '
            
            # main markets
            try:
                if i == 0:
                    main_markets = []
                    if all_data.count('Bets') == 2:
                        bets_index = all_data.index('Bets')
                        first_list = all_data[bets_index + 1:]
                        bets_index = first_list.index('Bets')
                        if entry['league'] == 'World Cup':
                            main_markets = first_list[bets_index + 1:bets_index + 14]
                        else:
                            main_markets = first_list[bets_index + 1:bets_index + 13]
                    else:
                        bets_index = all_data.index('Bets')
                        if entry['league'] == 'World Cup':
                            main_markets = first_list[bets_index + 1:bets_index + 14]
                        else:
                            main_markets = all_data[bets_index + 1:bets_index + 13]
                    for m in range(len(main_markets)):
                        main_markets[m] = main_markets[m].replace(" ", "")
                        main_markets[m] = main_markets[m].replace("(", "")
                        main_markets[m] = main_markets[m].replace(")", "")

                    spreads = {"key" : "spreads"}
                    h2h = {"key" : "h2h"}
                    totals = {"key" : "totals"}

                    spreads_elems = []
                    h2h_elems = []
                    totals_elems = []

                    if 'Spread' in all_data and 'Win' in all_data and 'Total' in all_data:
                        if entry['league'] == 'World Cup':
                            main_markets[0] = main_markets[0].split(',')
                            main_markets[2] = main_markets[2].split(',')
                            main_markets[8] = main_markets[8].split(',')
                            main_markets[11] = main_markets[11].split(',')
                            spreads_elems = main_markets[:4]
                            h2h_elems = main_markets[4:7]
                            totals_elems = main_markets[7:]
                        else:
                            spreads_elems = main_markets[:4]
                            h2h_elems = main_markets[4:6]
                            totals_elems = main_markets[6:]
                    elif 'Win' in all_data:
                        h2h_elems = main_markets
                    
                    if entry['league'] == 'World Cup':
                        outcomes = []
                        point = []
                        if len(spreads_elems[0]) == 2:
                            point.append(float(spreads_elems[0][0]) + float(spreads_elems[0][1]) / 2)
                            point.append(float(spreads_elems[2][0]) + float(spreads_elems[2][1]) / 2)
                        else:
                            point.append(float(spreads_elems[0][0]))
                            point.append(float(spreads_elems[2][0]))
                        outcomes.append({"name" : team1, "price" : int(spreads_elems[1]), "point" : point[0]})
                        outcomes.append({"name" : team2, "price" : int(spreads_elems[3]), "point" : point[1]})
                        spreads["outcomes"] = outcomes
                        markets_json_array.append(spreads)

                        outcomes = []
                        outcomes.append({"name" : team1, "price" : int(h2h_elems[0])})
                        outcomes.append({"name" : team2, "price" : int(h2h_elems[1])})
                        outcomes.append({"name" : "Draw", "price" : int(h2h_elems[2])})
                        h2h["outcomes"] = outcomes
                        print("h2h['outcomes']", h2h["outcomes"])
                        markets_json_array.append(h2h)

                        outcomes = []
                        point = None
                        if len(totals_elems[1]) == 2:
                            point = (float(totals_elems[1][0]) + float(totals_elems[1][1])) / 2
                        else:
                            point = float(totals_elems[1][0])
                        outcomes.append({"name" : "Over", "price" : int(totals_elems[2]), "point" : point})
                        outcomes.append({"name" : "Under", "price" : int(totals_elems[5]), "point" : point})
                        totals["outcomes"] = outcomes
                        markets_json_array.append(totals)
                    else:
                        outcomes = []
                        outcomes.append({"name" : team1, "price" : int(spreads_elems[1]), "point" : float(spreads_elems[0])})
                        outcomes.append({"name" : team2, "price" : int(spreads_elems[3]), "point" : float(spreads_elems[2])})
                        spreads["outcomes"] = outcomes
                        markets_json_array.append(spreads)

                        outcomes = []
                        outcomes.append({"name" : team1, "price" : int(h2h_elems[0])})
                        outcomes.append({"name" : team2, "price" : int(h2h_elems[1])})
                        h2h["outcomes"] = outcomes
                        markets_json_array.append(h2h)

                        outcomes = []
                        outcomes.append({"name" : "Over", "price" : int(totals_elems[2]), "point" : float(totals_elems[1])})
                        outcomes.append({"name" : "Under", "price" : int(totals_elems[5]), "point" : float(totals_elems[4])})
                        totals["outcomes"] = outcomes
                        markets_json_array.append(totals)

            except:
                print("   Failed on adding main markets")
                pass

            # alternate spreads
            try:
                if all_data[0] == " Spread " and "\xa0-\xa0First Half" not in all_data and "\xa0- Regulation Time" not in all_data and alternate_spread_flag == False:
                    alternate_spread_flag = True

                    spreads = all_data[3:]
                    if entry['league'] == 'World Cup':
                        for i in range(len(spreads)):
                            if len(spreads[i].split(',')) == 1:
                                continue
                            else:
                                spread_split = spreads[i].split(',')
                                spreads[i] = str((float(spread_split[0]) + float(spread_split[1])) / 2)
                
                    for s in range(len(spreads)):
                        spreads[s] = spreads[s].replace(" ", "")
                        spreads[s] = spreads[s].replace("(", "")
                        spreads[s] = spreads[s].replace(")", "")
                    
                
                    splits = list(split(spreads, 2))
                    first_half = splits[0]
                    second_half = splits[1]

                    for k in range(0, len(first_half), 2):
                        alternate_spreads_json = {"key" : "alternate_spreads"}
                        outcomes = []
                        outcomes.append({"name" : team1, "price" : int(first_half[k + 1]), "point" : float(first_half[k])})
                        outcomes.append({"name" : team2, "price" : int(second_half[k + 1]), "point" : float(second_half[k])})
                        alternate_spreads_json["outcomes"] = outcomes
                        markets_json_array.append(alternate_spreads_json)
                    all_data.clear()
                    all_attrs.clear()
                    continue
            except:
                print("   Failed on adding alternate spreads")
                pass
            
            # alternate totals
            try:
                if (all_data[0] == " Total Points " or all_data[0] == " Total Goals O/U ") and "\xa0-\xa0First Half" and not "\xa0-\xa0Live First Half" in all_data and alternate_totals_flag == False:
                    alternate_totals_flag = True

                    totals = all_data[3:]
                    if entry['league'] == 'World Cup':
                        for i in range(len(totals)):
                            if len(totals[i].split(',')) == 1:
                                continue
                            else:
                                totals_split = totals[i].split(',')
                                totals[i] = str((float(totals_split[0]) + float(totals_split[1])) / 2)

                    for t in range(len(totals)):
                        totals[t] = totals[t].replace(" ", "")
                        totals[t] = totals[t].replace("(", "")
                        totals[t] = totals[t].replace(")", "")

                    splits = list(split(totals, 3))
                    first_half = splits[0]
                    second_half = splits[1]
                    third_half = splits[2]
                    if len(first_half) != len(second_half) or len(first_half) != len(third_half) or len(second_half) != len(third_half):
                        all_data.clear()
                        all_attrs.clear()
                        continue

                    for k in range(len(first_half)):
                        alternate_totals_json = {"key" : "alternate_totals"}
                        outcomes = []
                        outcomes.append({"name" : "Over", "price" : int(second_half[k]), "point" : float(first_half[k])})
                        outcomes.append({"name" : "Under", "price" : int(third_half[k]), "point" : float(first_half[k])})
                        alternate_totals_json["outcomes"] = outcomes
                        markets_json_array.append(alternate_totals_json)
                    all_data.clear()
                    all_attrs.clear()
                    continue
            except:
                print("   Failed on adding alternate totals")
                pass
            all_data.clear()
            all_attrs.clear()

        response["markets"] = markets_json_array
        responses.append(response)
    driver.close()
    bovada_games = responses


def pinnacle_scraper(thread, entry):
    global pinnacle_games
    driver = webdriver.Chrome(options=options)
    driver.get(entry['link'])
    driver.implicitly_wait(5)

    elements = driver.find_elements(By.CLASS_NAME, 'style_btn__Fs5oS')
    #elements = driver.find_elements(By.XPATH, '//*[@id="events-chunkmode"]/div/div/div[2]/div/div[6]/a')
    links = []
    try:
        links = [i for i in [elem.get_attribute('href') for elem in elements] if i is not None]
    except:
        print("   Failed on retrieving href links")
    
    parser = Parser()

    responses = []
    for link in links:
        driver.get(link)
        print(thread, "scraping Pinnacle link:", link)

        try:
            # decimal odds -> american odds
            dropdown = driver.find_element(By.XPATH, '//*[@id="root"]/div/div[1]/div[4]/div/div/div[2]/div[2]')
            dropdown.click()
            american_odds = driver.find_element(By.XPATH, '//*[@id="root"]/div/div[1]/div[4]/div/div/div[2]/div[2]/div/div/div[2]/div/ul/li[2]')
            american_odds.click()
        except:
            print("   Failed on changing to American odds")
            continue
        
        try:
            game = driver.find_element(By.CLASS_NAME, 'style_desktop_last__2_upx') # <Washington Wizards @ Denver Nuggets>
        except:
            print("   Failed on finding game element")
            continue
        parser.feed(game.get_attribute('innerHTML'))

        # get teams playing
        teams = None
        if '@' in all_data[0]:
            teams = all_data[0].split('@')
        elif 'vs.' in all_data[0]:
            teams = all_data[0].split("vs.")
        team1 = teams[0][:-1]
        team2 = teams[1][1:]

        response = {"team1" : team1, "team2" : team2}

        all_data.clear()

        markets_json_array = []
        # do main markets by not clicking "See more"
        market_offline = False
        main_markets = driver.find_elements(By.CLASS_NAME, 'style_primary__3IwKt')
        spreads_elems = []
        h2h_elems = []
        totals_elems = []

        for m in main_markets:
            try:
                parser.feed(m.get_attribute('innerHTML'))
                if 'Market Offline' in all_data:
                    market_offline = True
                    break
                if all_data[0] == 'Money Line – Game' or all_data[0] == 'Money Line – OT Included' or all_data[0] == 'Money Line – Match':
                    h2h_elems = copy.deepcopy(all_data)
                elif all_data[0] == 'Handicap – Game' or all_data[0] == 'Handicap – OT Included' or all_data[0] == 'Handicap – Match':
                    spreads_elems = copy.deepcopy(all_data)
                elif all_data[0] == 'Total – Game' or all_data[0] == 'Total – OT Included' or all_data[0] == 'Total – Match':
                    totals_elems = copy.deepcopy(all_data)
                else:
                    all_data.clear()
                    continue
                all_data.clear()
            except:
                pass
        
        if market_offline:
            break
        
        spreads = {"key" : "spreads"}
        h2h = {"key" : "h2h"}
        totals = {"key" : "totals"}


        try:
            outcomes = []
            outcomes.append({"name" : team1, "price" : int(spreads_elems[4]), "point" : float(spreads_elems[3])})
            outcomes.append({"name" : team2, "price" : int(spreads_elems[6]), "point" : float(spreads_elems[5])})
            spreads["outcomes"] = outcomes
            markets_json_array.append(spreads)
        except:
            print("   Failed on adding spreads")
            pass

        try:
            if entry['league'] == 'World Cup':
                outcomes = []
                outcomes.append({"name" : team1, "price" : int(h2h_elems[2])})
                outcomes.append({"name" : "Draw", "price" : int(h2h_elems[4])})
                outcomes.append({"name" : team2, "price" : int(h2h_elems[6])})
                h2h["outcomes"] = outcomes
                markets_json_array.append(h2h)
                pass
            else:
                outcomes = []
                outcomes.append({"name" : team1, "price" : int(h2h_elems[2])})
                outcomes.append({"name" : team2, "price" : int(h2h_elems[4])})
                h2h["outcomes"] = outcomes
                markets_json_array.append(h2h)
        except: 
            print("   Failed on adding moneyline")
            pass

        try:
            outcomes = []
            outcomes.append({"name" : "Over", "price" : int(totals_elems[2]), "point" : float(totals_elems[1][5:])})
            outcomes.append({"name" : "Under", "price" : int(totals_elems[4]), "point" : float(totals_elems[1][5:])})
            totals["outcomes"] = outcomes
            markets_json_array.append(totals)
        except:
            print("   Failed on adding totals ")
            pass


        # alternate markets
        see_mores = driver.find_elements(By.CLASS_NAME, 'style_toggleMarketsText__yvcsI')
        for s in see_mores:
            s.click()
        markets = driver.find_elements(By.CLASS_NAME, 'style_primary__1bqk9')
        alternate_spreads_elems = []
        alternate_totals_elems = []

        for m in markets:
            parser.feed(m.get_attribute('innerHTML'))
            if all_data[0] == 'Handicap – Game' or all_data[0] == 'Handicap – OT Included' or all_data[0] == 'Handicap – Match':
                alternate_spreads_elems = copy.deepcopy(all_data)
            elif all_data[0] == 'Total – Game' or all_data[0] == 'Total – OT Included' or all_data[0] == 'Total – Game':
                alternate_totals_elems = copy.deepcopy(all_data)
            else:
                all_data.clear()
                continue
            all_data.clear()

        alternate_spreads_elems = alternate_spreads_elems[3:-1]
        alternate_totals_elems = alternate_totals_elems[1:-1]

        try:
            for i in range(0, len(alternate_spreads_elems), 4):
                alternate_spreads_json = {"key" : "alternate_spreads"}
                outcomes = []
                outcomes.append({"name" : team1, "price" : int(alternate_spreads_elems[i + 1]), "point" : float(alternate_spreads_elems[i])})
                outcomes.append({"name" : team2, "price" : int(alternate_spreads_elems[i + 3]), "point" : float(alternate_spreads_elems[i + 2])})
                alternate_spreads_json["outcomes"] = outcomes
                markets_json_array.append(alternate_spreads_json)
        except:
            print("   Failed on adding alternate spreads market")
            pass
        
        try:
            for i in range(0, len(alternate_totals_elems), 4):
                alternate_totals_json = {"key" : "alternate_totals"}
                outcomes = []
                point = alternate_totals_elems[i][5:]
                outcomes.append({"name" : "Over", "price" : int(alternate_totals_elems[i + 1]), "point" : float(point)})
                outcomes.append({"name" : "Under", "price" : int(alternate_totals_elems[i + 3]), "point" : float(point)})
                alternate_totals_json["outcomes"] = outcomes
                markets_json_array.append(alternate_totals_json)
        except:
            print("   Failed on adding alternate total market")
            pass

        all_data.clear()
        response["markets"] = markets_json_array
        responses.append(response)
    
    driver.close()
    pinnacle_games = responses

bovada_games = []
pinnacle_games = []
df = pd.DataFrame(columns = ['League', 'Event', 'Market', 'Bet Name', 'Odds', 'Bet Size', 'Exp. Value'])
try:
    os.rename(os.path.abspath(os.getcwd()) + "\live-betting.csv", os.path.abspath(os.getcwd()) + "\live-betting.csv")
    for i in range(len(bovada_sports)):
        thread1 = threading.Thread(target=bovada_scraper, args=("Thread 1", bovada_sports[i]))
        thread2 = threading.Thread(target=pinnacle_scraper, args=("Thread 2", pinnacle_sports[i]))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        league = bovada_sports[i]['league']

        # calculate no-vig odds from each market in each game on pinnacle and then EV from bovada
        for game in pinnacle_games:
            for market in game["markets"]:
                no_vig = {}
                if len(market['outcomes']) == 3: # 3 way outcome market
                    implied_prob1 = pb.implied_prob(market['outcomes'][0]['price'], category="us")[0]
                    implied_prob2 = pb.implied_prob(market['outcomes'][1]['price'], category="us")[0]
                    implied_prob3 = pb.implied_prob(market['outcomes'][2]['price'], category="us")[0]
                    juice = implied_prob1 + implied_prob2 + implied_prob3
                    no_vig_perc1 = implied_prob1 / juice
                    no_vig_perc2 = implied_prob2 / juice
                    no_vig_perc3 = implied_prob3 / juice
                    no_vig_percs = [no_vig_perc1, no_vig_perc2, no_vig_perc3]
                    for i in range(len(no_vig_percs)):
                        if no_vig_percs[i] < 0.5:
                            no_vig[market['outcomes'][i]['name']] = (100 / ((no_vig_percs[i] * 100) / 100)) - 100
                        else:
                            no_vig[market['outcomes'][i]['name']] = ((no_vig_percs[i] * 100) / (1 - ((no_vig_percs[i] * 100)/100))) * -1
                    market["no-vig"] = no_vig
                else:
                    implied_prob1 = pb.implied_prob(market['outcomes'][0]['price'], category="us")[0]
                    implied_prob2 = pb.implied_prob(market['outcomes'][1]['price'], category="us")[0]
                    juice = implied_prob1 + implied_prob2
                    no_vig_perc1 = implied_prob1 / juice
                    no_vig_perc2 = implied_prob2 / juice
                    if no_vig_perc1 > 0.5:
                        no_vig[market['outcomes'][0]['name']] = -(no_vig_perc1 / (1 - no_vig_perc1)) * 100
                        no_vig[market['outcomes'][1]['name']] = (1 - no_vig_perc2) / no_vig_perc2 * 100
                    else: 
                        no_vig[market['outcomes'][0]['name']] = (1 - no_vig_perc1) / no_vig_perc1 * 100
                        no_vig[market['outcomes'][1]['name']] = -(no_vig_perc2 / (1 - no_vig_perc2)) * 100
                    market["no-vig"] = no_vig

        for bovada_game in bovada_games:
            # find respective pinnacle game given this bovada_game
            pinnacle_index = next((i for i,d in enumerate(pinnacle_games) if d['team1'] == bovada_game['team1'] and d['team2'] == bovada_game['team2']), None)
            if pinnacle_index == None:
                continue
            pinnacle_game = pinnacle_games[pinnacle_index]

            final_markets = []
            # iterate through each market and calculate expected value for market
            for bovada_market in bovada_game["markets"]:
                final_market = {"league" : league, "event" : bovada_game['team1'] + " vs " + bovada_game['team2']}
                key = bovada_market['key']
                pinnacle_market = None
                if key == "alternate_spreads" or key == "alternate_totals":
                    point = bovada_market['outcomes'][0]['point']
                    alt_pinnacle_index = -1
                    try:
                        for index, market in enumerate(pinnacle_game['markets']):
                            if market['key'] == key:
                                if point == market['outcomes'][0]['point']:
                                    alt_pinnacle_index = index
                                    break
                    except:
                        pass
                    if alt_pinnacle_index == -1:
                        continue
                    pinnacle_market = pinnacle_game['markets'][alt_pinnacle_index]
                else:
                    pinnacle_market = next((item for item in pinnacle_game["markets"] if item["key"] == key), None)
                if pinnacle_market == None:
                    continue

                if (key == "spreads" or key == "totals") and bovada_market['outcomes'][0]['point'] != pinnacle_market['outcomes'][0]['point']:
                    continue

                # THIS IS IT --------------------------------------------------------------------------------
                if len(bovada_market['outcomes']) == 3:  # 3 way outcome market
                    expected_value = {}
                    kelly_bets = {}
                    implied_prob1 = 0
                    implied_prob2 = 0
                    implied_probs = {}
                    for i in range(3):
                        if pinnacle_market['no-vig'][pinnacle_market['outcomes'][i]['name']] > 0:
                            implied_prob = 100 / ((pinnacle_market['no-vig'][pinnacle_market['outcomes'][i]['name']] / 100) + 1)
                            implied_probs[pinnacle_market['outcomes'][i]['name']] = implied_prob
                        else:
                            implied_prob = 100 / ((100 / abs(pinnacle_market['no-vig'][pinnacle_market['outcomes'][i]['name']])) + 1)
                            implied_probs[pinnacle_market['outcomes'][i]['name']] = implied_prob
                    
                    for i in range(3):
                        if bovada_market['outcomes'][i]['price'] > 0:
                            ev = (bovada_market['outcomes'][i]['price'] * implied_probs[bovada_market['outcomes'][i]['name']] - 100 * (100 - implied_probs[bovada_market['outcomes'][i]['name']])) / 100
                            expected_value[bovada_market['outcomes'][i]['name']] = ev
                        else:
                            ev = (100 * implied_probs[bovada_market['outcomes'][i]['name']] - abs(bovada_market['outcomes'][i]['price']) * (100 - implied_probs[bovada_market['outcomes'][i]['name']])) / 100
                            expected_value[bovada_market['outcomes'][i]['name']] = ev
                        decimal_odds = pb.implied_odds(pb.implied_prob(bovada_market['outcomes'][i]['price'], category="us")[0], category="dec")[0]
                        winning_percentage = implied_probs[pinnacle_market['outcomes'][i]['name']] / 100
                        kelly = 0
                        if decimal_odds - 1 == 0:
                            kelly = 0
                        else:
                            kelly = ((decimal_odds - 1) * winning_percentage - (1 - winning_percentage)) / (decimal_odds - 1) * KELLY
                        kelly_bets[bovada_market['outcomes'][i]['name']] = kelly
                    bovada_market["expected_value"] = expected_value
                    bovada_market["kelly"] = kelly_bets
                    final_market["data"] = bovada_market
                # THIS IS THE END --------------------------------------------------------------------------------
                else:
                    expected_value = {}
                    kelly_bets = {}
                    implied_prob1 = 0
                    implied_prob2 = 0
                    implied_probs = {}
                    if pinnacle_market['no-vig'][pinnacle_market['outcomes'][0]['name']] > 0:
                        implied_prob1 = 100 / ((pinnacle_market['no-vig'][pinnacle_market['outcomes'][0]['name']] / 100) + 1)
                        implied_prob2 = 100 - implied_prob1
                        implied_probs[pinnacle_market['outcomes'][0]['name']] = implied_prob1
                        implied_probs[pinnacle_market['outcomes'][1]['name']] = implied_prob2
                    else:
                        implied_prob1 = 100 / ((100 / abs(pinnacle_market['no-vig'][pinnacle_market['outcomes'][0]['name']])) + 1)
                        implied_prob2 = 100 - implied_prob1
                        implied_probs[pinnacle_market['outcomes'][0]['name']] = implied_prob1
                        implied_probs[pinnacle_market['outcomes'][1]['name']] = implied_prob2
                    for i in range(2):
                        if bovada_market['outcomes'][i]['price'] > 0:
                            ev = (bovada_market['outcomes'][i]['price'] * implied_probs[bovada_market['outcomes'][i]['name']] - 100 * (100 - implied_probs[bovada_market['outcomes'][i]['name']])) / 100
                            expected_value[bovada_market['outcomes'][i]['name']] = ev
                        else:
                            ev = (100 * implied_probs[bovada_market['outcomes'][i]['name']] - abs(bovada_market['outcomes'][i]['price']) * (100 - implied_probs[bovada_market['outcomes'][i]['name']])) / 100
                            expected_value[bovada_market['outcomes'][i]['name']] = ev
                        decimal_odds = pb.implied_odds(pb.implied_prob(bovada_market['outcomes'][i]['price'], category="us")[0], category="dec")[0]
                        winning_percentage = implied_probs[pinnacle_market['outcomes'][i]['name']] / 100
                        kelly = 0
                        if decimal_odds - 1 == 0:
                            kelly = 0
                        else:
                            kelly = ((decimal_odds - 1) * winning_percentage - (1 - winning_percentage)) / (decimal_odds - 1) * KELLY
                        kelly_bets[bovada_market['outcomes'][i]['name']] = kelly
                    bovada_market["expected_value"] = expected_value
                    bovada_market["kelly"] = kelly_bets
                    final_market["data"] = bovada_market
            
                if final_market['data']['key'] == 'spreads':
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Point Spreads",
                        'Bet Name' : str(final_market['data']['outcomes'][0]['name']) + " " + str(final_market['data']['outcomes'][0]['point']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][0]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][0]['name']]
                    }, ignore_index = True)
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Point Spreads",
                        'Bet Name' : str(final_market['data']['outcomes'][1]['name']) + " " + str(final_market['data']['outcomes'][1]['point']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']], 2)),                    
                        'Odds' : final_market['data']['outcomes'][1]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][1]['name']]
                    }, ignore_index = True)
                
                elif final_market['data']['key'] == 'h2h':
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Moneyline",
                        'Bet Name' : str(final_market['data']['outcomes'][0]['name']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][0]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][0]['name']]
                    }, ignore_index = True)
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Moneyline",
                        'Bet Name' : str(final_market['data']['outcomes'][1]['name']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][1]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][1]['name']]
                    }, ignore_index = True)
                
                elif final_market['data']['key'] == 'totals':
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Totals",
                        'Bet Name' : str(final_market['data']['outcomes'][0]['name']) + " " + str(final_market['data']['outcomes'][0]['point']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][0]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][0]['name']]
                    }, ignore_index = True)
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Totals",
                        'Bet Name' : str(final_market['data']['outcomes'][1]['name']) + " " + str(final_market['data']['outcomes'][1]['point']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][1]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][1]['name']]
                    }, ignore_index = True)
                
                elif final_market['data']['key'] == 'alternate_spreads':
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Alternate Spreads",
                        'Bet Name' : str(final_market['data']['outcomes'][0]['name']) + " " + str(final_market['data']['outcomes'][0]['point']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][0]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][0]['name']]
                    }, ignore_index = True)
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Alternate Spreads",
                        'Bet Name' : str(final_market['data']['outcomes'][1]['name']) + " " + str(final_market['data']['outcomes'][1]['point']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][1]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][1]['name']]
                    }, ignore_index = True)
                
                elif final_market['data']['key'] == 'alternate_totals':
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Alternate Totals",
                        'Bet Name' : str(final_market['data']['outcomes'][0]['name']) + " " + str(final_market['data']['outcomes'][0]['point']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][0]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][0]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][0]['name']]
                    }, ignore_index = True)
                    df = df.append({'League': final_market['league'],
                        'Event' : final_market['event'],
                        'Market' : "Alternate Totals",
                        'Bet Name' : str(final_market['data']['outcomes'][1]['name']) + " " + str(final_market['data']['outcomes'][1]['point']),
                        'Bet Size': "$0" if final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']] < 0 else "$" + str(round(BANKROLL * final_market['data']['kelly'][final_market['data']['outcomes'][1]['name']], 2)),
                        'Odds' : final_market['data']['outcomes'][1]['price'],
                        'Exp. Value' : final_market['data']['expected_value'][final_market['data']['outcomes'][1]['name']]
                    }, ignore_index = True)
        bovada_games.clear()
        pinnacle_games.clear()
    df.drop_duplicates()
    sorted_df = df.sort_values(by=['Exp. Value'], ascending=False)
    sorted_df.to_csv('live-betting.csv', index=False)
    print(sorted_df.head(12))
except OSError as e:
    print('You have live-betting.csv open idiot')
    quit()