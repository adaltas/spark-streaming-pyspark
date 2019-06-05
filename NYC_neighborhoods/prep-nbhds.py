import shapefile
import json
with open('nbhd.jsonl', 'w') as outfile:
    sf = shapefile.Reader("ZillowNeighborhoods-NY")
    shapeRecs = sf.shapeRecords()
    for n in shapeRecs:
        State, County, City, Name, RegionID = n.record[:]
        if City != 'New York' : continue
        if County != 'New York' : continue # New York County corresponds to Manhattan borough
        json.dump({"name":Name, "coord":n.shape.points}, outfile)
        outfile.write('\n')
