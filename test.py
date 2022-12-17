team = "Dallas Stars"
index = team.index("St")
print(index + 2)
print(len(team))
if "State" not in team and team.index("St") + 2 == len(team):
    index = team.index("St")
    print(index)
    team = team.replace("St", "State")
print(team)