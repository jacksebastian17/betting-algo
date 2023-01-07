point1 = 'Over 19 Games'
point2 = 'Under 19 Games'
points = [point1, point2]
for p in points:
    point = p.replace('Over ', '')
    point = point.replace('Under ', '')
    point = point.replace(' Games', '')
    print(point)