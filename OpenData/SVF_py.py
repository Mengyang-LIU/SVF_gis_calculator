import os
import arcpy
from arcpy import env
arcpy.env.overwriteOutput = True
# Obtain a license for the ArcGIS 3D Analyst extension
arcpy.CheckOutExtension('3D')

# Set local variables
outLocation = r"\\Mac\Home\Documents\skyline_test\test"
inputDataLocation = r"\\Mac\Home\Documents\skyline_test"

points_2d = "agg_point.shp"  # The 2D point file
points_3d = "agg_point_3d.shp"  # The 3D point file
dem = "wuhan_building_3d1.shp" # the DEM file

points2File = os.path.join(inputDataLocation, points_2d)
points3File = os.path.join(inputDataLocation, points_3d)
demFile = os.path.join(inputDataLocation, dem)

# Set environment settings
env.workspace = outLocation

# Process: Create the empty table
outputFName = os.path.join(outLocation, "SVF.csv")
outputFile = open(outputFName, "w")

outputFile.write("ID,PercentOpenSky,PercentShade,MeanHorizAng,MeanZenithAng\n")

fcCursor = arcpy.SearchCursor(points2File)
for row in fcCursor:
    print(row)
    #create a temp shapefile with just one of our points
    whereClause = '"FID" = ' + str(row.FID)
    tmpSinglePoint2Shp = os.path.join(outLocation, str(row.FID) + "_2d.shp")
    arcpy.Select_analysis(points2File, tmpSinglePoint2Shp, whereClause)
    tmpSinglePoint3Shp = os.path.join(outLocation, str(row.FID) + "_3d.shp")
    arcpy.Select_analysis(points3File, tmpSinglePoint3Shp, whereClause)

    # create 500m radius 3d buffer from 2d point
    tmpSingleBufferShp = os.path.join(outLocation, "Buffer" + str(row.FID) + ".shp")
    arcpy.Buffer3D_3d(tmpSinglePoint2Shp, tmpSingleBufferShp, '500 Meters')
    # intersect with building file
    tmpSingleDemShp = os.path.join(outLocation, "Dem" + str(row.FID) + ".shp")
    arcpy.Intersect3D_3d(tmpSingleBufferShp, tmpSingleDemShp, demFile)

    # Execute Skyline
    tmpSingleLineShp = os.path.join(outLocation, "sky" + str(row.FID) + ".shp")
    arcpy.Skyline_3d(tmpSinglePoint3Shp, tmpSingleLineShp,tmpSingleDemShp)
    skyCursor = arcpy.SearchCursor(tmpSingleLineShp, "", "", "Shape_Leng", "")
        
    for rows in skyCursor:
        value = rows.getValue("Shape_Leng")
        if  value == 0:
            answerPercent = "NA"
            Shade = "NA"
            aveHoriz = "NA"
            aveZenith = "NA"
            outputFile.write(str(row.FID) + "," + str(answerPercent) + "," + str(Shade) + "," + str(aveHoriz) + "," + str(aveZenith) + "\n")

            arcpy.Delete_management(tmpSinglePoint2Shp)
            arcpy.Delete_management(tmpSinglePoint3Shp)
            arcpy.Delete_management(tmpSingleLineShp)
            print(str(row.FID) + "," + str(answerPercent) + "," + str(Shade) + "," + str(aveHoriz) + "," + str(aveZenith) + "\n")
        else: 

            #run the skylineGraph on temp output file
            tmpSinglePointOutTbl = os.path.join(outLocation, "t" + str(row.FID) + ".dbf")
            arcpy.SkylineGraph_3d(tmpSinglePoint3Shp, tmpSingleLineShp, 0, "ADDITIONAL_FIELDS", tmpSinglePointOutTbl)
     
            #manually calculate the average of the two fields we are interested in
            count = 0
            horizAngSum = 0
            zenithAngSum = 0
            for outputRow in arcpy.SearchCursor(tmpSinglePointOutTbl):
                horizAngSum += outputRow.HORIZ_ANG
                zenithAngSum += outputRow.ZENITH_ANG
                count += 1
    
            aveHoriz = horizAngSum / count
            aveZenith = zenithAngSum / count
    
            #this next section parses out their printed output and stores the 'Percent of sky in our CSV'
            msgText = arcpy.GetMessages()
            for line in msgText.split("\n"):
                if line.startswith("Percent of sky visible above a base vertical angle"):
                    answerPercent = line.split()[-1][:-1]
                    Shade = 100 - float(answerPercent)
    
            #write out the calculated answers to our CSV
            outputFile.write(str(row.FID) + "," + str(answerPercent) + "," + str(Shade) + "," + str(aveHoriz) + "," + str(aveZenith) + "\n")

            arcpy.Delete_management(tmpSinglePoint2Shp)
            arcpy.Delete_management(tmpSinglePoint3Shp)
            arcpy.Delete_management(tmpSingleBufferShp)
            arcpy.Delete_management(tmpSingleDemShp)
            arcpy.Delete_management(tmpSingleLineShp)
            arcpy.Delete_management(tmpSinglePointOutTbl)
            print(str(row.FID) + "," + str(answerPercent) + "," + str(Shade) + "," + str(aveHoriz) + "," + str(aveZenith) + "\n")
    
outputFile.close()
