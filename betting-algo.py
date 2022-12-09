import requests
import json
import pybettor as pb
import pandas as pd


sports = ['americanfootball_cfl', 'americanfootball_ncaaf', 'americanfootball_nfl', 'basketball_nba', 'basketball_ncaab', 'baseball_mlb', 'tennis_atp_french_open', 'icehockey_nhl']
#sports = ['americanfootball_ncaaf']

API_KEY1 = '52c641bafab4c4e8a22af3db9c04187f'
API_KEY2 = 'e3fffbba4feaff479a3dc83a6bfc2595'
API_KEY3 = '5c20020260c23df8c13f6c9549367d11'
API_KEY4 = 'e2d2191f31d9b678c5eaf1f7ea6882a8'
API_KEY5 = 'd33601e44f35dbbc6cf86c965988907e'
API_KEY6 = 'f9a4d25518274825f4a146f6892429e0'
API_KEY7 = '39df0ce4c6dd479d5be1d070ab95c979'
API_KEY8 = 'a5f6645633c01b1b64046973267f9f98'
API_KEY9 = '44dfc6c6c3ebee1d1447b30f8c7b9d2b'
MARKETS = 'h2h,spreads,totals'
ODDS_FORMAT = 'american'
BOOKMAKERS = 'bovada,pinnacle'
BANKROLL = 40
KELLY = 1


def check_requests(api_key):
    response = requests.get(f'https://api.the-odds-api.com/v4/sports/?apiKey={api_key}')
    if response.status_code != 200:
        print(f'Failed: status_code {response.status_code}, response body {response.text}')
    else:
        print('Remaining requests', response.headers['x-requests-remaining'])
        print('Used requests', response.headers['x-requests-used'])
#check_requests(API_KEY1)

odds_responses = []
for sport in sports:
    odds_response = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds', params={
        'api_key' : API_KEY9,
        'oddsFormat' : ODDS_FORMAT,
        'markets' : MARKETS,
        'bookmakers' : BOOKMAKERS
    })
    if odds_response.status_code != 200:
        print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')
    else:
        odds_responses.append(odds_response)


df = pd.DataFrame(columns = ['Event', 'Market', 'Bet Name', 'Odds', 'Bet Size', 'Exp. Value'])
for odds_response in odds_responses:
    json_response = odds_response.json()

    h2h_raw = []
    spreads_raw = []
    totals_raw = []
    for i in range(len(json_response)):
        if len(json_response[i]['bookmakers']) != 2:
            continue
        
        h2h_list = []
        spreads_list = []
        totals_list = []
        for bookmaker in json_response[i]['bookmakers']: # iterate through pinnacle and bovada books
            for market in bookmaker['markets']: # iterate through h2h, spreads, and totals markets
                data = {}
                data['key'] = bookmaker['key']
                data['event'] = json_response[i]['home_team'] + " vs " + json_response[i]['away_team']
                data['outcomes'] = market['outcomes']
                if market['key'] == 'h2h':
                    h2h_list.append(json.dumps(data))
                elif market['key'] == 'spreads':
                    spreads_list.append(json.dumps(data))
                elif market['key'] == 'totals':
                    totals_list.append(json.dumps(data))
        h2h_raw.append(h2h_list)
        spreads_raw.append(spreads_list)
        totals_raw.append(totals_list)

    h2h = []
    for h in h2h_raw:
        if len(h) != 2:
            continue
        new_h = []
        no_vig = {}
        bovada_first = False
        for book in h:
            new_h.append(book)
            book = json.loads(book)
            if book['key'] == 'pinnacle': # eliminate juice
                if bovada_first:
                    implied_prob1 = pb.implied_prob(book['outcomes'][0]['price'], category="us")[0]
                    implied_prob2 = pb.implied_prob(book['outcomes'][1]['price'], category="us")[0]
                    juice = implied_prob1 + implied_prob2
                    no_vig_perc1 = implied_prob1 / juice
                    no_vig_perc2 = implied_prob2 / juice
                    if no_vig_perc1 > 0.5:
                        no_vig[book['outcomes'][0]['name']] = -(no_vig_perc1 / (1 - no_vig_perc1)) * 100
                        no_vig[book['outcomes'][1]['name']] = (1 - no_vig_perc2) / no_vig_perc2 * 100
                    else: 
                        no_vig[book['outcomes'][0]['name']] = (1 - no_vig_perc1) / no_vig_perc1 * 100
                        no_vig[book['outcomes'][1]['name']] = -(no_vig_perc2 / (1 - no_vig_perc2)) * 100
                    no_vig_entry = {}
                    no_vig_entry['no_vig'] = no_vig
                    new_h.append(json.dumps(no_vig_entry))

                    expected_value = {}
                    kelly_bets = {}
                    for i in range(2):
                        implied_prob1 = 0
                        implied_prob2 = 0
                        if no_vig[book['outcomes'][i]['name']] > 0:
                            implied_prob1 = 100 / ((no_vig[book['outcomes'][i]['name']] / 100) + 1)
                            implied_prob2 = 100 - implied_prob1
                        else:
                            implied_prob1 = 100 / ((100 / abs(no_vig[book['outcomes'][i]['name']])) + 1)
                            implied_prob2 = 100 - implied_prob1
                        if book['outcomes'][i]['price'] > 0:
                            ev = (book['outcomes'][i]['price'] * implied_prob1 - 100 * implied_prob2) / 100
                            expected_value[book['outcomes'][i]['name']] = ev
                        else:
                            ev = (100 * implied_prob1 - abs(book['outcomes'][i]['price']) * implied_prob2) / 100
                            expected_value[book['outcomes'][i]['name']] = ev
                        decimal_odds = pb.implied_odds(pb.implied_prob(book['outcomes'][i]['price'], category="us")[0], category="dec")[0]
                        winning_percentage = implied_prob1 / 100
                        kelly = 0
                        if decimal_odds - 1 == 0:
                            kelly = 0
                        else:
                            kelly = ((decimal_odds - 1) * winning_percentage - (1 - winning_percentage)) / (decimal_odds - 1) * KELLY
                        kelly_bets[book['outcomes'][i]['name']] = kelly
                    ev_entry = {}
                    ev_entry['ev'] = expected_value
                    kelly_entry = {}
                    kelly_entry['kelly'] = kelly_bets
                    new_h.append(json.dumps(ev_entry))
                    new_h.append(json.dumps(kelly_entry))

                    h2h.append(new_h)
                    bovada_first = False
                    continue

                implied_prob1 = pb.implied_prob(book['outcomes'][0]['price'], category="us")[0]
                implied_prob2 = pb.implied_prob(book['outcomes'][1]['price'], category="us")[0]
                juice = implied_prob1 + implied_prob2
                no_vig_perc1 = implied_prob1 / juice
                no_vig_perc2 = implied_prob2 / juice
                if no_vig_perc1 > 0.5:
                    no_vig[book['outcomes'][0]['name']] = -(no_vig_perc1 / (1 - no_vig_perc1)) * 100
                    no_vig[book['outcomes'][1]['name']] = (1 - no_vig_perc2) / no_vig_perc2 * 100
                else:
                    no_vig[book['outcomes'][0]['name']] = (1 - no_vig_perc1) / no_vig_perc1 * 100
                    no_vig[book['outcomes'][1]['name']] = -(no_vig_perc2 / (1 - no_vig_perc2)) * 100
                no_vig_entry = {}
                no_vig_entry['no_vig'] = no_vig
                new_h.append(json.dumps(no_vig_entry))
            else:
                if no_vig == {}:
                    bovada_first = True
                    continue
                expected_value = {}
                kelly_bets = {}
                for i in range(2):
                    implied_prob1 = 0
                    implied_prob2 = 0
                    if no_vig[book['outcomes'][i]['name']] > 0:
                        implied_prob1 = 100 / ((no_vig[book['outcomes'][i]['name']] / 100) + 1)
                        implied_prob2 = 100 - implied_prob1
                    else:
                        implied_prob1 = 100 / ((100 / abs(no_vig[book['outcomes'][i]['name']])) + 1)
                        implied_prob2 = 100 - implied_prob1
                    if book['outcomes'][i]['price'] > 0:
                        ev = (book['outcomes'][i]['price'] * implied_prob1 - 100 * implied_prob2) / 100
                        expected_value[book['outcomes'][i]['name']] = ev
                    else:
                        ev = (100 * implied_prob1 - abs(book['outcomes'][i]['price']) * implied_prob2) / 100
                        expected_value[book['outcomes'][i]['name']] = ev
                    decimal_odds = pb.implied_odds(pb.implied_prob(book['outcomes'][i]['price'], category="us")[0], category="dec")[0]
                    winning_percentage = implied_prob1 / 100
                    kelly = 0
                    if decimal_odds - 1 == 0:
                        kelly = 0
                    else:
                        kelly = ((decimal_odds - 1) * winning_percentage - (1 - winning_percentage)) / (decimal_odds - 1) * KELLY
                    kelly_bets[book['outcomes'][i]['name']] = kelly
                ev_entry = {}
                ev_entry['ev'] = expected_value
                kelly_entry = {}
                kelly_entry['kelly'] = kelly_bets
                new_h.append(json.dumps(ev_entry))
                new_h.append(json.dumps(kelly_entry))
        h2h.append(new_h)

    spreads = []
    for s in spreads_raw:
        if len(s) != 2:
            continue
        new_s = []
        no_vig = {}
        bovada_first = False
        if abs(float(json.loads(s[0])['outcomes'][0]['point'])) != abs(float(json.loads(s[1])['outcomes'][0]['point'])): # point spread is not the same between books
            continue
        first_point = 0
        second_point = 0
        for book in s:
            new_s.append(book)
            book = json.loads(book)
            if book['key'] == 'pinnacle': # eliminate juice
                first_point = book['outcomes'][0]['point']
                if bovada_first:
                    implied_prob1 = pb.implied_prob(book['outcomes'][0]['price'], category="us")[0]
                    implied_prob2 = pb.implied_prob(book['outcomes'][1]['price'], category="us")[0]
                    juice = implied_prob1 + implied_prob2
                    no_vig_perc1 = implied_prob1 / juice
                    no_vig_perc2 = implied_prob2 / juice
                    if no_vig_perc1 > 0.5:
                        no_vig[book['outcomes'][0]['name']] = -(no_vig_perc1 / (1 - no_vig_perc1)) * 100
                        no_vig[book['outcomes'][1]['name']] = (1 - no_vig_perc2) / no_vig_perc2 * 100
                    else: 
                        no_vig[book['outcomes'][0]['name']] = (1 - no_vig_perc1) / no_vig_perc1 * 100
                        no_vig[book['outcomes'][1]['name']] = -(no_vig_perc2 / (1 - no_vig_perc2)) * 100
                    no_vig_entry = {}
                    no_vig_entry['no_vig'] = no_vig
                    new_s.append(json.dumps(no_vig_entry))

                    expected_value = {}
                    kelly_bets = {}
                    for i in range(2):
                        implied_prob1 = 0
                        implied_prob2 = 0
                        if no_vig[book['outcomes'][i]['name']] > 0:
                            implied_prob1 = 100 / ((no_vig[book['outcomes'][i]['name']] / 100) + 1)
                            implied_prob2 = 100 - implied_prob1
                        else:
                            implied_prob1 = 100 / ((100 / abs(no_vig[book['outcomes'][i]['name']])) + 1)
                            implied_prob2 = 100 - implied_prob1
                        if book['outcomes'][i]['price'] > 0:
                            ev = (book['outcomes'][i]['price'] * implied_prob1 - 100 * implied_prob2) / 100
                            expected_value[book['outcomes'][i]['name']] = ev
                        else:
                            ev = (100 * implied_prob1 - abs(book['outcomes'][i]['price']) * implied_prob2) / 100
                            expected_value[book['outcomes'][i]['name']] = ev
                        decimal_odds = pb.implied_odds(pb.implied_prob(book['outcomes'][i]['price'], category="us")[0], category="dec")[0]
                        winning_percentage = implied_prob1 / 100
                        kelly = 0
                        if decimal_odds - 1 == 0:
                            kelly = 0
                        else:
                            kelly = ((decimal_odds - 1) * winning_percentage - (1 - winning_percentage)) / (decimal_odds - 1) * KELLY
                        kelly_bets[book['outcomes'][i]['name']] = kelly
                    ev_entry = {}
                    ev_entry['ev'] = expected_value
                    kelly_entry = {}
                    kelly_entry['kelly'] = kelly_bets
                    new_s.append(json.dumps(ev_entry))
                    new_s.append(json.dumps(kelly_entry))

                    spreads.append(new_s)
                    bovada_first = False
                    continue

                implied_prob1 = pb.implied_prob(book['outcomes'][0]['price'], category="us")[0]
                implied_prob2 = pb.implied_prob(book['outcomes'][1]['price'], category="us")[0]
                juice = implied_prob1 + implied_prob2
                no_vig_perc1 = implied_prob1 / juice
                no_vig_perc2 = implied_prob2 / juice
                if no_vig_perc1 > 0.5:
                    no_vig[book['outcomes'][0]['name']] = -(no_vig_perc1 / (1 - no_vig_perc1)) * 100
                    no_vig[book['outcomes'][1]['name']] = (1 - no_vig_perc2) / no_vig_perc2 * 100
                else: 
                    no_vig[book['outcomes'][0]['name']] = (1 - no_vig_perc1) / no_vig_perc1 * 100
                    no_vig[book['outcomes'][1]['name']] = -(no_vig_perc2 / (1 - no_vig_perc2)) * 100
                no_vig_entry = {}
                no_vig_entry['no_vig'] = no_vig
                new_s.append(json.dumps(no_vig_entry))
            else:
                if no_vig == {}:
                    bovada_first = True
                    continue
                flip = False
                second_point = book['outcomes'][0]['point']
                if (first_point != second_point):
                    flip = True
                expected_value = {}
                kelly_bets = {}
                for i in range(2):
                    implied_prob1 = 0
                    implied_prob2 = 0
                    if no_vig[book['outcomes'][i]['name']] > 0:
                        implied_prob1 = 100 / ((no_vig[book['outcomes'][i]['name']] / 100) + 1)
                        implied_prob2 = 100 - implied_prob1
                    else:
                        implied_prob1 = 100 / ((100 / abs(no_vig[book['outcomes'][i]['name']])) + 1)
                        implied_prob2 = 100 - implied_prob1
                    
                    if flip == True:
                        implied_prob1 = 100 - implied_prob1
                        implied_prob2 = 100 - implied_prob2
                    if book['outcomes'][i]['price'] > 0:
                        ev = (book['outcomes'][i]['price'] * implied_prob1 - 100 * implied_prob2) / 100
                        expected_value[book['outcomes'][i]['name']] = ev
                    else:
                        ev = (100 * implied_prob1 - abs(book['outcomes'][i]['price']) * implied_prob2) / 100
                        expected_value[book['outcomes'][i]['name']] = ev
                    decimal_odds = pb.implied_odds(pb.implied_prob(book['outcomes'][i]['price'], category="us")[0], category="dec")[0]
                    winning_percentage = implied_prob1 / 100
                    kelly = 0
                    if decimal_odds - 1 == 0:
                        kelly = 0
                    else:
                        kelly = ((decimal_odds - 1) * winning_percentage - (1 - winning_percentage)) / (decimal_odds - 1) * KELLY
                    kelly_bets[book['outcomes'][i]['name']] = kelly
                flip = False
                ev_entry = {}
                ev_entry['ev'] = expected_value
                kelly_entry = {}
                kelly_entry['kelly'] = kelly_bets
                new_s.append(json.dumps(ev_entry))
                new_s.append(json.dumps(kelly_entry))
        spreads.append(new_s)


    totals = []
    for t in totals_raw:
        if (len(t) != 2) or (json.loads(t[0])['outcomes'][0]['point'] != json.loads(t[1])['outcomes'][0]['point']): # O/U point line isn't the same
            continue
        new_t = []
        no_vig = {}
        bovada_first = False
        for book in t:
            new_t.append(book)
            book = json.loads(book)
            if book['key'] == 'pinnacle': # eliminate juice
                if bovada_first:
                    implied_prob1 = pb.implied_prob(book['outcomes'][0]['price'], category="us")[0]
                    implied_prob2 = pb.implied_prob(book['outcomes'][1]['price'], category="us")[0]
                    juice = implied_prob1 + implied_prob2
                    no_vig_perc1 = implied_prob1 / juice
                    no_vig_perc2 = implied_prob2 / juice
                    if no_vig_perc1 > 0.5:
                        no_vig[book['outcomes'][0]['name']] = -(no_vig_perc1 / (1 - no_vig_perc1)) * 100
                        no_vig[book['outcomes'][1]['name']] = (1 - no_vig_perc2) / no_vig_perc2 * 100
                    else: 
                        no_vig[book['outcomes'][0]['name']] = (1 - no_vig_perc1) / no_vig_perc1 * 100
                        no_vig[book['outcomes'][1]['name']] = -(no_vig_perc2 / (1 - no_vig_perc2)) * 100
                    no_vig_entry = {}
                    no_vig_entry['no_vig'] = no_vig
                    new_t.append(json.dumps(no_vig_entry))

                    expected_value = {}
                    kelly_bets = {}
                    for i in range(2):
                        implied_prob1 = 0
                        implied_prob2 = 0
                        if no_vig[book['outcomes'][i]['name']] > 0:
                            implied_prob1 = 100 / ((no_vig[book['outcomes'][i]['name']] / 100) + 1)
                            implied_prob2 = 100 - implied_prob1
                        else:
                            implied_prob1 = 100 / ((100 / abs(no_vig[book['outcomes'][i]['name']])) + 1)
                            implied_prob2 = 100 - implied_prob1
                        if book['outcomes'][i]['price'] > 0:
                            ev = (book['outcomes'][i]['price'] * implied_prob1 - 100 * implied_prob2) / 100
                            expected_value[book['outcomes'][i]['name']] = ev
                        else:
                            ev = (100 * implied_prob1 - abs(book['outcomes'][i]['price']) * implied_prob2) / 100
                            expected_value[book['outcomes'][i]['name']] = ev
                        decimal_odds = pb.implied_odds(pb.implied_prob(book['outcomes'][i]['price'], category="us")[0], category="dec")[0]
                        winning_percentage = implied_prob1 / 100
                        kelly = 0
                        if decimal_odds - 1 == 0:
                            kelly = 0
                        else:
                            kelly = ((decimal_odds - 1) * winning_percentage - (1 - winning_percentage)) / (decimal_odds - 1) * KELLY
                        kelly_bets[book['outcomes'][i]['name']] = kelly
                    ev_entry = {}
                    ev_entry['ev'] = expected_value
                    kelly_entry = {}
                    kelly_entry['kelly'] = kelly_bets
                    new_t.append(json.dumps(ev_entry))
                    new_t.append(json.dumps(kelly_entry))

                    totals.append(new_t)
                    bovada_first = False
                    continue

                implied_prob1 = pb.implied_prob(book['outcomes'][0]['price'], category="us")[0]
                implied_prob2 = pb.implied_prob(book['outcomes'][1]['price'], category="us")[0]
                juice = implied_prob1 + implied_prob2
                no_vig_perc1 = implied_prob1 / juice
                no_vig_perc2 = implied_prob2 / juice
                if no_vig_perc1 > 0.5:
                    no_vig[book['outcomes'][0]['name']] = -(no_vig_perc1 / (1 - no_vig_perc1)) * 100
                    no_vig[book['outcomes'][1]['name']] = (1 - no_vig_perc2) / no_vig_perc2 * 100
                else: 
                    no_vig[book['outcomes'][0]['name']] = (1 - no_vig_perc1) / no_vig_perc1 * 100
                    no_vig[book['outcomes'][1]['name']] = -(no_vig_perc2 / (1 - no_vig_perc2)) * 100
                no_vig_entry = {}
                no_vig_entry['no_vig'] = no_vig
                new_t.append(json.dumps(no_vig_entry))
            else:
                if no_vig == {}:
                    bovada_first = True
                    continue
                expected_value = {}
                kelly_bets = {}
                for i in range(2):
                    implied_prob1 = 0
                    implied_prob2 = 0
                    if no_vig[book['outcomes'][i]['name']] > 0:
                        implied_prob1 = 100 / ((no_vig[book['outcomes'][i]['name']] / 100) + 1)
                        implied_prob2 = 100 - implied_prob1
                    else:
                        implied_prob1 = 100 / ((100 / abs(no_vig[book['outcomes'][i]['name']])) + 1)
                        implied_prob2 = 100 - implied_prob1
                    if book['outcomes'][i]['price'] > 0:
                        ev = (book['outcomes'][i]['price'] * implied_prob1 - 100 * implied_prob2) / 100
                        expected_value[book['outcomes'][i]['name']] = ev
                    else:
                        ev = (100 * implied_prob1 - abs(book['outcomes'][i]['price']) * implied_prob2) / 100
                        expected_value[book['outcomes'][i]['name']] = ev
                    decimal_odds = pb.implied_odds(pb.implied_prob(book['outcomes'][i]['price'], category="us")[0], category="dec")[0]
                    winning_percentage = implied_prob1 / 100
                    kelly = 0
                    if decimal_odds - 1 == 0:
                        kelly = 0
                    else:
                        kelly = ((decimal_odds - 1) * winning_percentage - (1 - winning_percentage)) / (decimal_odds - 1) * KELLY
                    kelly_bets[book['outcomes'][i]['name']] = kelly
                ev_entry = {}
                ev_entry['ev'] = expected_value
                kelly_entry = {}
                kelly_entry['kelly'] = kelly_bets
                new_t.append(json.dumps(ev_entry))
                new_t.append(json.dumps(kelly_entry))
        totals.append(new_t)

    #odd_counter = 0
    for h in h2h:
        #odd_counter += 1
        #if odd_counter % 2 == 0:
        #    continue
        h.sort()
        df = df.append({'Event' : json.loads(h[3])['event'], 
            'Market' : 'Moneyline', 
            'Bet Name' : json.loads(h[2])['outcomes'][0]['name'],
            'Odds' : json.loads(h[2])['outcomes'][0]['price'],
            'Bet Size': "$0" if json.loads(h[1])['kelly'][json.loads(h[2])['outcomes'][0]['name']] < 0 else "$" + str(round(BANKROLL * json.loads(h[1])['kelly'][json.loads(h[2])['outcomes'][0]['name']], 2)),
            'Exp. Value' : json.loads(h[0])['ev'][json.loads(h[2])['outcomes'][0]['name']]
            }, ignore_index = True)
        
        df = df.append({'Event' : json.loads(h[3])['event'], 
            'Market' : 'Moneyline', 
            'Bet Name' : json.loads(h[2])['outcomes'][1]['name'],
            'Odds' : json.loads(h[2])['outcomes'][1]['price'],
            'Bet Size': "$0" if json.loads(h[1])['kelly'][json.loads(h[2])['outcomes'][1]['name']] < 0 else "$" + str(round(BANKROLL * json.loads(h[1])['kelly'][json.loads(h[2])['outcomes'][1]['name']], 2)),
            'Exp. Value' : json.loads(h[0])['ev'][json.loads(h[2])['outcomes'][1]['name']]
            }, ignore_index = True)

    #odd_counter = 0
    for s in spreads:
        #odd_counter += 1
        #if odd_counter % 2 == 0:
        #    continue
        s.sort()
        df = df.append({'Event' : json.loads(s[3])['event'], 
            'Market' : 'Point Spread', 
            'Bet Name' : str(json.loads(s[2])['outcomes'][0]['name']) + " " + str(json.loads(s[2])['outcomes'][0]['point']),
            'Odds' : json.loads(s[2])['outcomes'][0]['price'],
            'Bet Size': "$0" if json.loads(s[1])['kelly'][json.loads(s[2])['outcomes'][0]['name']] < 0 else "$" + str(round(BANKROLL * json.loads(s[1])['kelly'][json.loads(s[2])['outcomes'][0]['name']], 2)),
            'Exp. Value' : json.loads(s[0])['ev'][json.loads(s[2])['outcomes'][0]['name']]
            }, ignore_index = True)
        
        df = df.append({'Event' : json.loads(s[3])['event'], 
            'Market' : 'Point Spread', 
            'Bet Name' : str(json.loads(s[2])['outcomes'][1]['name']) + " " + str(json.loads(s[2])['outcomes'][1]['point']),
            'Odds' : json.loads(s[2])['outcomes'][1]['price'],
            'Bet Size': "$0" if json.loads(s[1])['kelly'][json.loads(s[2])['outcomes'][1]['name']] < 0 else "$" + str(round(BANKROLL * json.loads(s[1])['kelly'][json.loads(s[2])['outcomes'][1]['name']], 2)),
            'Exp. Value' : json.loads(s[0])['ev'][json.loads(s[2])['outcomes'][1]['name']]
            }, ignore_index = True)

    #odd_counter = 0
    for t in totals:
        #odd_counter += 1
        #if odd_counter % 2 == 0:
        #    continue
        t.sort()
        df = df.append({'Event' : json.loads(t[3])['event'],
            'Market' : 'Totals', 
            'Bet Name' : str(json.loads(t[2])['outcomes'][0]['name']) + " " + str(json.loads(t[2])['outcomes'][0]['point']),
            'Odds' : json.loads(t[2])['outcomes'][0]['price'],
            'Bet Size': "$0" if json.loads(t[1])['kelly'][json.loads(t[2])['outcomes'][0]['name']] < 0 else "$" + str(round(BANKROLL * json.loads(t[1])['kelly'][json.loads(t[2])['outcomes'][0]['name']], 2)),
            'Exp. Value' : json.loads(t[0])['ev'][json.loads(t[2])['outcomes'][0]['name']]
            }, ignore_index = True)
        
        df = df.append({'Event' : json.loads(t[3])['event'],
            'Market' : 'Totals', 
            'Bet Name' : str(json.loads(t[2])['outcomes'][1]['name']) + " " + str(json.loads(t[2])['outcomes'][1]['point']),
            'Odds' : json.loads(t[2])['outcomes'][1]['price'],
            'Bet Size': "$0" if json.loads(t[1])['kelly'][json.loads(t[2])['outcomes'][1]['name']] < 0 else "$" + str(round(BANKROLL * json.loads(t[1])['kelly'][json.loads(t[2])['outcomes'][1]['name']], 2)),
            'Exp. Value' : json.loads(t[0])['ev'][json.loads(t[2])['outcomes'][1]['name']]
            }, ignore_index = True)
    

sorted_df = df.sort_values(by=['Exp. Value'], ascending=False)
sorted_df.to_csv('live-betting.csv', index=False)
print(sorted_df.head(12))
print('Remaining requests', odds_response.headers['x-requests-remaining'])
print('Used requests', odds_response.headers['x-requests-used'])