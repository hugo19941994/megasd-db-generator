#Image Quantizer for SNES Graphics v1.2
#Written by Khaz
#Takes in a 24bpp Bitmap file no larger than 256x256 pixels and quantizes it into 15-colour palettes.  Width and height must be divisible by 8 pixels (1 tile)
#Intelligently merges similar palettes to reduce to 8 or fewer total palettes, then exports SNES-friendly .inc files containing tile sets, tile map and palettes.

#Changes since 1.1:
#   -b flag added to switch to binary file output.
#   Binary files are arranged Tile Set, Tile Map then Palettes
#   Tile Set and Tile Map data size scales with height of image, Palette data size is static

#Changes since 1.0:
#   No longer fails when all tiles contain less than 15 colours
#   All square roots were totally unnececssary and have been removed since 1.0 for slight improvement in speed
#   Optional # of tile set rows to output for smaller pictures, default is to write fullscreen image

#Potential future enhancements:
#   Change optional bitmap outputs and tilemap padding into command line arguments rather than commented-out code.
#   Use of Background colour for a 16th colour in each palette for increased colour depth.
#   Option of 16x16 tiles
#   Optimizing for Speed 
#   Option of RMS instead of straight Averages for colour comparisons (pointless?)
#   Option to match very-close colours between palettes, to make tile borders less visible (????)

import argparse
import random
import math
import struct

parser = argparse.ArgumentParser(description='Quantize a 24bpp Bitmap (max 256x256) into SNES format.', epilog="Image dimensions must be divisible by 8.  File must be located in current directory.")
parser.add_argument('FileName', help='File Name (NO PATH OR EXTENSION)')
parser.add_argument("-t", "--trials", nargs=1, default=[2], type=int, help="Number of trials per quantization")
parser.add_argument("-l", "--loops", nargs=1, default=[60], type=int, help="Maximum number of loops per trial")
parser.add_argument("-p", "--palettes", nargs=1, default=[8], type=int, help="Target Number of Palettes (Must be <=8 for SNES output)")
parser.add_argument("-c", "--chunking", nargs=1, default=[24], type=int, help="Comparison Chunking - # to compare before merging best (8-128)")
parser.add_argument("-x", "--xtraQ", nargs=1, default=[3], type=int, help="Quantize all palettes after merging is complete for __ more trials")
parser.add_argument("-o", "--outputRows", nargs=1, default=[32], type=int, help="Rows of tile set to output")
parser.add_argument("-b", "--binaryOut", action='store_true', default=False, help="Write output as binary files as well")
args = parser.parse_args()

print(args.FileName)

inputFileName = "{}.bmp".format(args.FileName)
outputBMPNameA = "{}MaxPals.bmp".format(args.FileName)
outputBMPNameB = "{}NoEmptyPals.bmp".format(args.FileName)
outputBMPNameC = "{}CrushedPals.bmp".format(args.FileName)

outputIncNameA = "{}.inc".format(args.FileName)
outputIncNameALabel = "{}:".format(args.FileName)
outputIncNameB = "{}Map.inc".format(args.FileName)
outputIncNameBLabel = "{}Map:".format(args.FileName)
outputIncNameC = "{}Palettes.inc".format(args.FileName)
outputIncNameCLabel = "{}Palettes:".format(args.FileName)

outputBinNameA = "{}.bin".format(args.FileName)

targetNumPalettes = args.palettes[0]
trials = args.trials[0]
qLoops = args.loops[0]
xTrials = args.xtraQ[0]
chunkSize = args.chunking[0]
RowsToOutput = args.outputRows[0]
binOut = args.binaryOut
if chunkSize < 8 or chunkSize > 128:
    chunkSize = 24

bytelist = []
outputBytelist = []

print ("Reading Input File")

with open(inputFileName, "rb") as f:
    while True:
        byte = f.read(1)
        if not byte:
            break
        bytelist.append(byte)
        
if bytelist[0] != b'B' or bytelist[1] != b'M':
    print ("This is not a bitmap.  Aborting.")
    quit()

print ("Bytes Read: {}".format(len(bytelist)))

if len(bytelist) < 40:
    print("Input file is too small to even be a bitmap!  What are you trying to pull here?")
    quit()
    
print ("Reading Header")

pixelStartAddress = (ord(bytelist[10])*1)+(ord(bytelist[11])*256)+(ord(bytelist[12])*65536)+(ord(bytelist[13])*16777216)
dibHeaderSize = (ord(bytelist[14])*1)+(ord(bytelist[15])*256)+(ord(bytelist[16])*65536)+(ord(bytelist[17])*16777216)
bitmapWidth = (ord(bytelist[18])*1)+(ord(bytelist[19])*256)+(ord(bytelist[20])*65536)+(ord(bytelist[21])*16777216)
bitmapHeight = (ord(bytelist[22])*1)+(ord(bytelist[23])*256)+(ord(bytelist[24])*65536)+(ord(bytelist[25])*16777216)
colourPlanes = (ord(bytelist[26])*1)+(ord(bytelist[27])*256)
bitsPerPixel = (ord(bytelist[28])*1)+(ord(bytelist[29])*256)
compressionMethod = (ord(bytelist[30])*1)+(ord(bytelist[31])*256)+(ord(bytelist[32])*65536)+(ord(bytelist[33])*16777216)

if dibHeaderSize != 40:
    print ("Invalid DIB Header size.  Non-Windows BMP DIB Headers are not supported at this time.")
    quit()
if bitmapWidth > 256:
    print ("Invalid data in DIB Header:  Bitmap is Too Wide at {}".format(bitmapWidth))
    quit()
if bitmapHeight > 256:
    print ("Invalid data in DIB Header:  Bitmap is Too Wide at {}".format(bitmapHeight))
    quit()
if bitmapWidth%8 != 0 or bitmapHeight%8 != 0:
    print ("Bitmap Dimensions Must Be Divisible By 8 (1 Tile).  Sorry.")
if colourPlanes != 1:
    print ("Invalid data in DIB Header:  Colour Planes must equal 1")
    quit()
if bitsPerPixel != 24:
    print ("Invalid data in DIB Header:  BitsPerPixel must equal 24")
    quit()
if compressionMethod != 0:
    print ("Bitmap is compressed.  Compressed files are not supported at this time.")
    quit()

numTilesWide = bitmapWidth//8
numTilesTall = bitmapHeight//8
numPalettes = (numTilesWide * numTilesTall)

print ("pixelstartaddress: {}".format(pixelStartAddress))
print ("bitmapwidth: {}".format(bitmapWidth))
print ("bitmapheight: {}".format(bitmapHeight))
print ("colourplanes: {}".format(colourPlanes))
print ("bitsperpixel: {}".format(bitsPerPixel))
print ("compressionmethod: {}".format(compressionMethod))
print ("bitmapwidth(8x8 tiles): {}".format(numTilesWide))
print ("bitmapheight(8x8 tiles): {}".format(numTilesTall))


#=======================================================================================================================
#delcare data arrays

prevIndexes = [0 for x in range(14)]
prevClrs = [[0 for x in range(3)] for x in range(14)]

tileClrsR = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileClrsG = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileClrsB = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileUniqueClrsR = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileUniqueClrsG = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileUniqueClrsB = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileUniqueClrsNumPix = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileUniqueClrsPalClr = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileUniqueClrsPalDist = [[[0 for x in range(64)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileClrsNumUniqueClrs = [[0 for x in range(numTilesWide)] for x in range(numTilesTall)]

tileWorkingPalR = [0 for x in range(15)]
tileWorkingPalG = [0 for x in range(15)]
tileWorkingPalB = [0 for x in range(15)]
tileWorkingPalNumPix = [0 for x in range(15)]
tileWorkingPalNumClrs = [0 for x in range(15)]

tileBestPalR = [[[0 for x in range(15)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileBestPalG = [[[0 for x in range(15)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileBestPalB = [[[0 for x in range(15)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileBestPalNumPix = [[[0 for x in range(15)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileBestPalNumClrs = [[[0 for x in range(15)] for x in range(numTilesWide)] for x in range(numTilesTall)]
tileBestPalAvg = [[0 for x in range(numTilesWide)] for x in range(numTilesTall)]
tileBestPalRMS = [[0 for x in range(numTilesWide)] for x in range(numTilesTall)]

tileEMergePalR = [[0 for x in range(15)] for x in range(numPalettes)]
tileEMergePalG = [[0 for x in range(15)] for x in range(numPalettes)]
tileEMergePalB = [[0 for x in range(15)] for x in range(numPalettes)]
tileEMergePalNumPix = [[0 for x in range(15)] for x in range(numPalettes)]
tileEMergePalNumClrs = [[0 for x in range(15)] for x in range(numPalettes)]
tileEMergePalAvg = [0 for x in range(numPalettes)]
tileEMergePalRMS = [0 for x in range(numPalettes)]

tileEMergeBestPalR = [0 for x in range(15)]
tileEMergeBestPalG = [0 for x in range(15)]
tileEMergeBestPalB = [0 for x in range(15)]
tileEMergeBestPalNumPix = [0 for x in range(15)]
tileEMergeBestPalNumClrs = [0 for x in range(15)]

tileEMergePalNumTiles = [0 for x in range(numPalettes)]
tileEMergePalTileList = [[[0 for x in range(2)] for x in range(numPalettes)] for x in range(numPalettes)]

tileMergePalR = [[0 for x in range(15)] for x in range(numPalettes)]
tileMergePalG = [[0 for x in range(15)] for x in range(numPalettes)]
tileMergePalB = [[0 for x in range(15)] for x in range(numPalettes)]
tileMergePalNumPix = [[0 for x in range(15)] for x in range(numPalettes)]
tileMergePalNumClrs = [[0 for x in range(15)] for x in range(numPalettes)]
tileMergePalAvg = [0 for x in range(numPalettes)]
tileMergePalRMS = [0 for x in range(numPalettes)]

tileMergePalNumTiles = [0 for x in range(numPalettes)]
tileMergePalTileList = [[[0 for x in range(2)] for x in range(numPalettes)] for x in range(numPalettes)]

emptyPalList = [0 for x in range(numPalettes)]
fullPalList = [0 for x in range(numPalettes)]
tempPalList = [0 for x in range(numPalettes)]

sumDistance = [0 for x in range(15)]

tileDataOutputArray = [[0 for x in range(256)] for x in range(256)]
bitplane0 = ["" for x in range(8)]
bitplane1 = ["" for x in range(8)]
bitplane2 = ["" for x in range(8)]
bitplane3 = ["" for x in range(8)]

#load arrays with bitmap data
for i in range(bitmapHeight):
    for j in range(bitmapWidth):
        tileCoordY = i%8
        tileCoordX = j%8
        mapCoordY = i//8
        mapCoordX = j//8
        tileClrsB[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX] = ord(bytelist[pixelStartAddress+(((i*bitmapWidth)+j)*3)])//8
        tileClrsG[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX] = ord(bytelist[pixelStartAddress+(((i*bitmapWidth)+j)*3)+1])//8
        tileClrsR[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX] = ord(bytelist[pixelStartAddress+(((i*bitmapWidth)+j)*3)+2])//8       
#        if tileCoordY == 0:
#            print("R: {},{},{}".format(i, j, tileClrsR[tileCoordY][tileCoordX][(tileCoordY*8)+tileCoordX]))

#check for duplicate colours, calculate number of unique colours in each tile
for i in range(numTilesTall):
    for j in range(numTilesWide):
        tileClrsNumUniqueClrs[i][j] = 0  #initialize all to 0 and add 1 when a match is not found
        tileBestPalAvg[i][j] = 999999      #initialize all "best" palettes' averages to 999999
        #tileBestPalRMS[i][j] = 999999    
        
for i in range(numTilesTall):
    for j in range(numTilesWide):
        for k in range(64):
            matchfound = False
            for n in range(tileClrsNumUniqueClrs[i][j]):
                if (tileClrsB[i][j][k] == tileUniqueClrsB[i][j][n]) and (tileClrsG[i][j][k] == tileUniqueClrsG[i][j][n]) and (tileClrsR[i][j][k] == tileUniqueClrsR[i][j][n]):
                    matchfound = True
                    tileUniqueClrsNumPix[i][j][n] = tileUniqueClrsNumPix[i][j][n] + 1
                    break
            if matchfound == False:
                tileUniqueClrsR[i][j][tileClrsNumUniqueClrs[i][j]] = tileClrsR[i][j][k]
                tileUniqueClrsG[i][j][tileClrsNumUniqueClrs[i][j]] = tileClrsG[i][j][k]
                tileUniqueClrsB[i][j][tileClrsNumUniqueClrs[i][j]] = tileClrsB[i][j][k]
                tileUniqueClrsNumPix[i][j][tileClrsNumUniqueClrs[i][j]] = 1
                tileClrsNumUniqueClrs[i][j] = tileClrsNumUniqueClrs[i][j] + 1                
                    
#=======================================================================================================================
#Do initial quantization of each individual 8x8 tile

for i in range(numTilesTall):
    for j in range(numTilesWide):
        bestAvgClrDistance = 999999
        #bestRMSClrDistance = 999999
        print("building palette from {} unique clrs...  {},{}".format(tileClrsNumUniqueClrs[i][j], i, j))
        for k in range(trials):
            reshuffleAttempts = 0
            gettingWorseCounter = 0
            avgClrDistance = 999999
            prevAvgClrDistance = 999999
               
            if tileClrsNumUniqueClrs[i][j] > 15:
                n = 0
                while n < 15:
                    randomIndex = random.randint(0, (tileClrsNumUniqueClrs[i][j]-1)) #Inclusive
                    tileWorkingPalR[n] = tileUniqueClrsR[i][j][randomIndex]
                    tileWorkingPalG[n] = tileUniqueClrsG[i][j][randomIndex]
                    tileWorkingPalB[n] = tileUniqueClrsB[i][j][randomIndex]

                    reroll = False
                    for m in range(n):
                        if randomIndex == prevIndexes[m]:
                            #print ("reroll")
                            reroll = True
                            break
                    
                    if reroll == False:
                        if n < 14:
                            prevIndexes[n] = randomIndex
                        n = n + 1
            else:
                #scan down the list, load in each unique colour, then break - no quantizing to do
                for n in range(tileClrsNumUniqueClrs[i][j]):
                    tileBestPalR[i][j][n] = tileUniqueClrsR[i][j][n]
                    tileBestPalG[i][j][n] = tileUniqueClrsG[i][j][n]
                    tileBestPalB[i][j][n] = tileUniqueClrsB[i][j][n]
                    tileBestPalNumPix[i][j][n] = 1        #THIS VALUE IS WRONG BUT I AM BANKING ON IT NOT MATTERING
                    tileBestPalNumClrs[i][j][n] = 1
                tileBestPalAvg[i][j] = 0
                #tileBestPalRMS[i][j] = 0

                break

            #now quantize the working palette!
            convergCounter = 0
            for qLoop in range(qLoops):
#                print("{},{} Trial: {}  Loop: {},  avg{}  prev{}".format(i, j, k, qLoop, avgClrDistance, prevAvgClrDistance))

                prevAvgClrDistance = avgClrDistance
                
                paletteReady = False
                while paletteReady == False:
                    for n in range(15):
                        tileWorkingPalNumPix[n] = 0
                        tileWorkingPalNumClrs[n] = 0

                    avgClrDistance = 0
                    #RMSClrDistance = 0

                    #find each colour's closest palette colour and store distance
                    for n in range(tileClrsNumUniqueClrs[i][j]):
                        closestPixelDistance = 999999
                        for m in range(15):
                            pixelDistance = ((tileUniqueClrsR[i][j][n] - tileWorkingPalR[m]) ** 2) + ((tileUniqueClrsG[i][j][n] - tileWorkingPalG[m]) ** 2) + ((tileUniqueClrsB[i][j][n] - tileWorkingPalB[m]) ** 2)
                            #pixelDistance = math.sqrt(pixelDistance)
                            if pixelDistance < closestPixelDistance:
                                closestPixelDistance = pixelDistance
                                closestPixelColour = m
                        tileUniqueClrsPalClr[i][j][n] = closestPixelColour
                        tileUniqueClrsPalDist[i][j][n] = closestPixelDistance
                        tileWorkingPalNumPix[closestPixelColour] = tileWorkingPalNumPix[closestPixelColour] + tileUniqueClrsNumPix[i][j][n]
                        tileWorkingPalNumClrs[closestPixelColour] = tileWorkingPalNumClrs[closestPixelColour] + 1
                        
                        avgClrDistance = avgClrDistance + (closestPixelDistance * tileUniqueClrsNumPix[i][j][n])
                        #RMSClrDistance = RMSClrDistance + ((closestPixelDistance * closestPixelDistance) * tileUniqueClrsNumPix[i][j][n])

                    #Check if any palette colours are unused
                    #if so reassign colour to most distant and recalculate, IFF there are enough colours to fill a palette
                    paletteReady = True

                    if tileClrsNumUniqueClrs[i][j] > 14:
                        for n in range(15):
                            if tileWorkingPalNumPix[n] == 0:
                                paletteReady = False
    
                                mostClrDistance = 0
                                mostDistantClr = 0
                                for m in range(tileClrsNumUniqueClrs[i][j]):
                                    if tileUniqueClrsPalDist[i][j][m] > mostClrDistance:
                                        mostClrDistance = tileUniqueClrsPalDist[i][j][m]
                                        mostDistantClr = m
                                        
                                tileWorkingPalR[n] = tileUniqueClrsR[i][j][mostDistantClr]
                                tileWorkingPalG[n] = tileUniqueClrsG[i][j][mostDistantClr]
                                tileWorkingPalB[n] = tileUniqueClrsB[i][j][mostDistantClr]
                                
                avgClrDistance = (avgClrDistance/64)
                #RMSClrDistance = math.sqrt(RMSClrDistance/64)

                #Compute new colour centres for each palette slot.  (workingpalnumpix is not changed here)
                for n in range(15):
                    tileWorkingPalR[n] = 0
                    tileWorkingPalG[n] = 0
                    tileWorkingPalB[n] = 0

                    for m in range(tileClrsNumUniqueClrs[i][j]):
                        if tileUniqueClrsPalClr[i][j][m] == n:
                            tileWorkingPalR[n] = tileWorkingPalR[n] + (tileUniqueClrsR[i][j][m] * tileUniqueClrsNumPix[i][j][m])
                            tileWorkingPalG[n] = tileWorkingPalG[n] + (tileUniqueClrsG[i][j][m] * tileUniqueClrsNumPix[i][j][m])
                            tileWorkingPalB[n] = tileWorkingPalB[n] + (tileUniqueClrsB[i][j][m] * tileUniqueClrsNumPix[i][j][m])

                    tileWorkingPalR[n] = tileWorkingPalR[n] / tileWorkingPalNumPix[n]
                    tileWorkingPalG[n] = tileWorkingPalG[n] / tileWorkingPalNumPix[n]
                    tileWorkingPalB[n] = tileWorkingPalB[n] / tileWorkingPalNumPix[n]

                if not qLoop == 0:
#                    print("{} - {}".format(avgClrDistance, tileBestPalAvg[i][j]))
                    if avgClrDistance < tileBestPalAvg[i][j]:
                        #we have a new best!  Store the palette
#                        print("New Best Found!  {}".format(avgClrDistance))
                        for n in range(15):
                            tileBestPalR[i][j][n] = tileWorkingPalR[n]
                            tileBestPalG[i][j][n] = tileWorkingPalG[n]
                            tileBestPalB[i][j][n] = tileWorkingPalB[n]
                            tileBestPalNumPix[i][j][n] = tileWorkingPalNumPix[n]
                            tileBestPalNumClrs[i][j][n] = tileWorkingPalNumClrs[n]
                            tileBestPalAvg[i][j] = avgClrDistance
                            #tileBestPalRMS[i][j] = RMSClrDistance
                    
                    if avgClrDistance > prevAvgClrDistance:
                        gettingWorseCounter = gettingWorseCounter + 1
                    else:
                        gettingWorseCounter = 0
                    if avgClrDistance == prevAvgClrDistance:
                        convergCounter = convergCounter + 1
                    else:
                        convergCounter = 0
                    if convergCounter > 2 or gettingWorseCounter > 3:
                        if reshuffleAttempts > 5:
                            break
                        else:
#                            print("Reshuffle!")
                            gettingWorseCounter = 0
                            convergCounter = 0
                            reshuffleAttempts = reshuffleAttempts + 1

                            #merge two closest centroids...

                            mergeSumClosest = 999999
                            for n in range(15):
                                for m in range(n):
                                    #removed a math.sqrt here
                                    mergeSum = ((tileWorkingPalR[n] - tileWorkingPalR[m]) ** 2) + ((tileWorkingPalG[n] - tileWorkingPalG[m]) ** 2) + ((tileWorkingPalB[n] - tileWorkingPalB[m]) ** 2)
                                    if mergeSum < mergeSumClosest:
                                        mergeSumClosest = mergeSum
                                        mergeSumIndexA = m
                                        mergeSumIndexB = n

                            #replace first centroid with average of two being merged
                            tileWorkingPalR[mergeSumIndexA] = (tileWorkingPalR[mergeSumIndexA] + tileWorkingPalR[mergeSumIndexB]) / 2
                            tileWorkingPalG[mergeSumIndexA] = (tileWorkingPalG[mergeSumIndexA] + tileWorkingPalG[mergeSumIndexB]) / 2
                            tileWorkingPalB[mergeSumIndexA] = (tileWorkingPalB[mergeSumIndexA] + tileWorkingPalB[mergeSumIndexB]) / 2

                            #replace second centroid with most distant point of most populated (with colors not pixels) cluster
                            splitDist = 0
                            mergeSumIndexA = 0    #we can reuse IndexA now since it's done

                            for n in range(15):
                                if tileWorkingPalNumClrs[n] > splitDist:
                                    splitDist = tileWorkingPalNumClrs[n]
                                    mergeSumIndexA = n

                            splitDist = 0
                            splitIndex = 0
                            for n in range(tileClrsNumUniqueClrs[i][j]):
                                if tileUniqueClrsPalClr[i][j][n] == mergeSumIndexA:
                                    if tileUniqueClrsPalDist[i][j][n] > splitDist:
                                        splitDist = tileUniqueClrsPalDist[i][j][n]
                                        splitIndex = n

                            tileWorkingPalR[mergeSumIndexB] = tileUniqueClrsR[i][j][splitIndex]
                            tileWorkingPalG[mergeSumIndexB] = tileUniqueClrsG[i][j][splitIndex]
                            tileWorkingPalB[mergeSumIndexB] = tileUniqueClrsB[i][j][splitIndex]

#=======================================================================================================================
#Initial Quantization Done.  Dump a quick bitmap to confirm it worked so far

#print("Exporting Max-Palettes Bitmap...")

#with open(outputBMPNameA, "wb") as f:

    #Copy original header back verbatim
#    for i in range(pixelStartAddress):
#        f.write(bytelist[i])

    #Then write new pixel data
#    for i in range(bitmapHeight):
#        for j in range(bitmapWidth):
#            tileCoordY = i%8
#            tileCoordX = j%8
#            mapCoordY = i//8
#            mapCoordX = j//8

#            bestPixelDistance = 999999
            #for each pixel, lookup which best palette to use (mapCoordY, mapCoordX), find the closest colour match in it, then write that colour value
#            for n in range(15):
#                pixelDistance = ((tileBestPalR[mapCoordY][mapCoordX][n] - tileClrsR[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)
#                pixelDistance = pixelDistance + ((tileBestPalG[mapCoordY][mapCoordX][n] - tileClrsG[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)
#                pixelDistance = pixelDistance + ((tileBestPalB[mapCoordY][mapCoordX][n] - tileClrsB[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)

#                if pixelDistance < bestPixelDistance:
#                    bestPixelDistance = pixelDistance
#                    bestClrMatch = n
                    
#            f.write(struct.pack("B", int(tileBestPalB[mapCoordY][mapCoordX][bestClrMatch] * 8)))
#            f.write(struct.pack("B", int(tileBestPalG[mapCoordY][mapCoordX][bestClrMatch] * 8)))
#            f.write(struct.pack("B", int(tileBestPalR[mapCoordY][mapCoordX][bestClrMatch] * 8)))

#Transfer "Best Palettes" arrays into merging arrays indexed by raw palette number

print("Shuffling Data...")

for i in range(numTilesTall):
    for j in range(numTilesWide):
        x = (i * numTilesWide) + j
        
        tileEMergePalAvg[x] = tileBestPalAvg[i][j]
        #tileEMergePalRMS[x] = tileBestPalRMS[i][j]

        tileEMergePalNumTiles[x] = 1
        tileEMergePalTileList[x][0][0] = i
        tileEMergePalTileList[x][0][1] = j

        for n in range(15):
            tileEMergePalR[x][n] = tileBestPalR[i][j][n]
            tileEMergePalG[x][n] = tileBestPalG[i][j][n]
            tileEMergePalB[x][n] = tileBestPalB[i][j][n]
            tileEMergePalNumPix[x][n] = tileBestPalNumPix[i][j][n]
            tileEMergePalNumClrs[x][n] = tileBestPalNumClrs[i][j][n]

#=======================================================================================================================
#Begin Merging Palettes
#find best fit for every palette with an empty slot and merge them away first
            
#compile separate lists of full and not full palettes
emptyPals = 0
fullPals = 0
for i in range(numPalettes):
    emptyPalFound = False
    for n in range(15):
        if tileEMergePalNumPix[i][n] == 0:
            emptyPalList[emptyPals] = i
            emptyPals = emptyPals + 1
            emptyPalFound = True
            break
    if emptyPalFound == False:
        fullPalList[fullPals] = i
        fullPals = fullPals + 1

while fullPals < targetNumPalettes:
    #scan through empty palettes and collect unique colours until a new full palette has been built
    print("Pre-Merging away palettes with empty slots...  {} empty, {} full".format(emptyPals, fullPals))
    collectedColours = 0
    alreadyGotColour = False
    collectionPalCount = 0

    for n in range(15):
        tileWorkingPalNumPix[n] = 0
        tileWorkingPalNumClrs[n] = 1
        
    for x in range(emptyPals):
        i = emptyPalList[x]
        tileHi = tileEMergePalTileList[i][0][0]
        tileLo = tileEMergePalTileList[i][0][1]
        
        collectionPalCount = collectionPalCount + 1

        for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
            alreadyGotColour = False
            for n in range(collectedColours):
                if tileUniqueClrsR[tileHi][tileLo][m] == tileWorkingPalR[n] and tileUniqueClrsG[tileHi][tileLo][m] == tileWorkingPalG[n] and tileUniqueClrsB[tileHi][tileLo][m] == tileWorkingPalB[n]:
                    alreadyGotColour = True
                    tileWorkingPalNumPix[n] = tileWorkingPalNumPix[n] + tileUniqueClrsNumPix[tileHi][tileLo][m]
                    break
                
            if alreadyGotColour == False:
                tileWorkingPalR[collectedColours] = tileUniqueClrsR[tileHi][tileLo][m]
                tileWorkingPalG[collectedColours] = tileUniqueClrsG[tileHi][tileLo][m]
                tileWorkingPalB[collectedColours] = tileUniqueClrsB[tileHi][tileLo][m]
                collectedColours = collectedColours + 1
                print("Got a new Colour! {}".format(collectedColours))
                
                if collectedColours == 15:
                    break
                
        if collectedColours == 15:
            break

    if collectedColours == 15:    
        print("Full Palette of Colours Found!  Merging {} nonfull palettes together".format(collectionPalCount))
        for n in range(collectionPalCount - 1):
            j = emptyPalList[n]
            tileEMergePalTileList[i][tileEMergePalNumTiles[i]][0] = tileEMergePalTileList[j][0][0]
            tileEMergePalTileList[i][tileEMergePalNumTiles[i]][1] = tileEMergePalTileList[j][0][1]
            tileEMergePalNumTiles[i] = tileEMergePalNumTiles[i] + 1
                
        for m in range(15):
            tileEMergePalR[i][m] = tileWorkingPalR[m]
            tileEMergePalG[i][m] = tileWorkingPalG[m]
            tileEMergePalB[i][m] = tileWorkingPalB[m]
            tileEMergePalNumPix[i][m] = tileWorkingPalNumPix[m]
            tileEMergePalNumClrs[i][m] = 1                #Somehow I dont think this will matter

        fullPalList[fullPals] = i
        fullPals = fullPals + 1

        #now recreate the emptypals list starting from the next element, if there is one
        transferredPals = 0
        for n in range(emptyPals - x - 1):
            tempPalList[n] = emptyPalList[x + n + 1]
            transferredPals = transferredPals + 1
        if transferredPals == 0:
            emptyPals = 0
            break
        else:
            for m in range(transferredPals):
                emptyPalList[m] = tempPalList[m]
            emptyPals = transferredPals

            
        
    else:
        print("RAN OUT OF COLOURS TO MERGE!  Merging entire empty palette list ending")
        i = emptyPalList[emptyPals - 1]
        for n in range(emptyPals - 1):
            j = emptyPalList[n]
            tileEMergePalTileList[i][tileEMergePalNumTiles[i]][0] = tileEMergePalTileList[j][0][0]
            tileEMergePalTileList[i][tileEMergePalNumTiles[i]][1] = tileEMergePalTileList[j][0][1]
            tileEMergePalNumTiles[i] = tileEMergePalNumTiles[i] + 1
                
        for m in range(15):
            tileEMergePalR[i][m] = tileWorkingPalR[m]
            tileEMergePalG[i][m] = tileWorkingPalG[m]
            tileEMergePalB[i][m] = tileWorkingPalB[m]
            tileEMergePalNumPix[i][m] = tileWorkingPalNumPix[m]
            tileEMergePalNumClrs[i][m] = 1                #Somehow I dont think this will matter
            tileEMergePalAvg[i] = 9         #Hopefully trigger a good quantize later?

        fullPalList[fullPals] = i
        fullPals = fullPals + 1
        emptyPals = 0
        break
    
#=======================================================================================================================    
print("Merging away palettes with empty slots...  {} empty, {} full".format(emptyPals, fullPals))

#test the empty palettes' tiles for compatibility with each full palette, shove it in where it fits best
#when finished, re-quantize the ones that were merged?

for x in range(emptyPals):
    i = emptyPalList[x]
    closestFullPal = 0
    closestFullPalDist = 999999
    
    #numTiles of the unfull palette will always be 1 here since we haven't begun merging yet.  No loop.
    tileHi = tileEMergePalTileList[i][0][0]
    tileLo = tileEMergePalTileList[i][0][1]

    for y in range(fullPals):
        j = fullPalList[y]
        
        totalMergePaletteDistance = 0

        for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
            shortestDistance = 0

            for k in range(15):
                #removed a math.sqrt here
                sumDistance[k] = ((tileEMergePalR[j][k] - tileUniqueClrsR[tileHi][tileLo][m]) ** 2) + ((tileEMergePalG[j][k] - tileUniqueClrsG[tileHi][tileLo][m]) ** 2) + ((tileEMergePalB[j][k] - tileUniqueClrsB[tileHi][tileLo][m]) ** 2)

                if k != 0:
                    if sumDistance[k] < sumDistance[shortestDistance]:
                        shortestDistance = k

            totalMergePaletteDistance = totalMergePaletteDistance + (sumDistance[shortestDistance] * tileUniqueClrsNumPix[tileHi][tileLo][m])

        if totalMergePaletteDistance < closestFullPalDist:
            closestFullPalDist = totalMergePaletteDistance
            closestFullPal = j
            
    #Merge unfull palette into best matching full palette - copy tile number over, increment it's numtiles
    print("Merging Not-Full Palette {} into {} and Quantizing".format(i, closestFullPal))
    tileEMergePalTileList[closestFullPal][tileEMergePalNumTiles[closestFullPal]][0] = tileEMergePalTileList[i][0][0]
    tileEMergePalTileList[closestFullPal][tileEMergePalNumTiles[closestFullPal]][1] = tileEMergePalTileList[i][0][1]
    tileEMergePalNumTiles[closestFullPal] = tileEMergePalNumTiles[closestFullPal] + 1

    #FULLY QUANTIZE the merged palette EVERY TIME.  Get random start point from palette's tiles
    bestAvgClrDistance = 999999
    #bestRMSClrDistance = 999999
    for k in range(trials):
        reshuffleAttempts = 0
        gettingWorseCounter = 0
        avgClrDistance = 999999
        prevAvgClrDistance = 999999
           
        n = 0
        while n < 15:
            randomIndex = random.randint(0, tileEMergePalNumTiles[closestFullPal]-1)
            tileHi = tileEMergePalTileList[closestFullPal][randomIndex][0]
            tileLo = tileEMergePalTileList[closestFullPal][randomIndex][1]
            
            randomIndex = random.randint(0, (tileClrsNumUniqueClrs[tileHi][tileLo]-1)) #Inclusive
            tileEMergePalR[closestFullPal][n] = tileUniqueClrsR[tileHi][tileLo][randomIndex]
            tileEMergePalG[closestFullPal][n] = tileUniqueClrsG[tileHi][tileLo][randomIndex]
            tileEMergePalB[closestFullPal][n] = tileUniqueClrsB[tileHi][tileLo][randomIndex]

            reroll = False
            for m in range(n):
                if tileEMergePalR[closestFullPal][n] == prevClrs[m][0] and tileEMergePalG[closestFullPal][n] == prevClrs[m][1] and tileEMergePalB[closestFullPal][n] == prevClrs[m][2]:
                    reroll = True
                    break
                    
            if reroll == False:
                if n < 14:
                    prevClrs[n][0] = tileEMergePalR[closestFullPal][n]
                    prevClrs[n][1] = tileEMergePalG[closestFullPal][n]
                    prevClrs[n][2] = tileEMergePalB[closestFullPal][n]
                n = n + 1

        #now quantize it!
        convergCounter = 0
        for qLoop in range(qLoops):
            #print("{} Trial: {}  Loop: {},  avg{}  prev{}".format(i, k, qLoop, avgClrDistance, prevAvgClrDistance))

            prevAvgClrDistance = avgClrDistance

            paletteReady = False
            while paletteReady == False:
                for n in range(15):
                    tileEMergePalNumPix[closestFullPal][n] = 0
                    tileEMergePalNumClrs[closestFullPal][n] = 0

                avgClrDistance = 0
                #RMSClrDistance = 0

                #find each colour's closest palette colour and store distance
                for p in range(tileEMergePalNumTiles[closestFullPal]):
                    tileHi = tileEMergePalTileList[closestFullPal][p][0]
                    tileLo = tileEMergePalTileList[closestFullPal][p][1]
                    
                    for n in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                        closestPixelDistance = 999999
                        for m in range(15):
                            pixelDistance = ((tileUniqueClrsR[tileHi][tileLo][n] - tileEMergePalR[closestFullPal][m]) ** 2) + ((tileUniqueClrsG[tileHi][tileLo][n] - tileEMergePalG[closestFullPal][m]) ** 2) + ((tileUniqueClrsB[tileHi][tileLo][n] - tileEMergePalB[closestFullPal][m]) ** 2)
                            #pixelDistance = math.sqrt(pixelDistance)
                            if pixelDistance < closestPixelDistance:
                                closestPixelDistance = pixelDistance
                                closestPixelColour = m
                        tileUniqueClrsPalClr[tileHi][tileLo][n] = closestPixelColour
                        tileUniqueClrsPalDist[tileHi][tileLo][n] = closestPixelDistance

                        tileEMergePalNumPix[closestFullPal][closestPixelColour] = tileEMergePalNumPix[closestFullPal][closestPixelColour] + tileUniqueClrsNumPix[tileHi][tileLo][n]         
                        tileEMergePalNumClrs[closestFullPal][closestPixelColour] = tileEMergePalNumClrs[closestFullPal][closestPixelColour] + 1
                        
                        avgClrDistance = avgClrDistance + (closestPixelDistance * tileUniqueClrsNumPix[tileHi][tileLo][n])
                        #RMSClrDistance = RMSClrDistance + ((closestPixelDistance * closestPixelDistance) * tileUniqueClrsNumPix[tileHi][tileLo][n])

                #Check if any palette colours are unused.  If so replace it with the most distant colour
                #if so reassign colour to most distant and recalculate.  There will ALWAYS be enough colours to fill a palette here.
                paletteReady = True
                for n in range(15):
                    if tileEMergePalNumPix[closestFullPal][n] == 0:
                        paletteReady = False
                        #print("omgpalettenotready - {}, {}".format(tileEMergePalNumPix[closestFullPal][n], n))
    
                        mostClrDistance = 0
                        mostDistantClr = 0
                        for p in range(tileEMergePalNumTiles[closestFullPal]):
                            tileHi = tileEMergePalTileList[closestFullPal][p][0]
                            tileLo = tileEMergePalTileList[closestFullPal][p][1]
                                
                            for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                if tileUniqueClrsPalDist[tileHi][tileLo][m] > mostClrDistance:
                                    mostClrDistance = tileUniqueClrsPalDist[tileHi][tileLo][m]
                                    mostDistantClr = m
                                    mostDistantTileHi = tileHi
                                    mostDistantTileLo = tileLo
                                        
                        tileEMergePalR[closestFullPal][n] = tileUniqueClrsR[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                        tileEMergePalG[closestFullPal][n] = tileUniqueClrsG[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                        tileEMergePalB[closestFullPal][n] = tileUniqueClrsB[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                                
            avgClrDistance = (avgClrDistance/(tileEMergePalNumTiles[closestFullPal]*64))
            #RMSClrDistance = math.sqrt(RMSClrDistance/(tileEMergePalNumTiles[closestFullPal]*64))

            if avgClrDistance < bestAvgClrDistance:
                #we have a new best!  Store the palette
                print("New Best Found!  {}".format(avgClrDistance))
                for n in range(15):
                    tileEMergeBestPalR[n] = tileEMergePalR[closestFullPal][n]
                    tileEMergeBestPalG[n] = tileEMergePalG[closestFullPal][n]
                    tileEMergeBestPalB[n] = tileEMergePalB[closestFullPal][n]
                    tileEMergeBestPalNumPix[n] = tileEMergePalNumPix[closestFullPal][n]
                    tileEMergeBestPalNumClrs[n] = tileEMergePalNumClrs[closestFullPal][n]
                bestAvgClrDistance = avgClrDistance
                #bestRMSClrDistance = RMSClrDistance
                            
            #calculate new palette colours
            for n in range(15):
                tileEMergePalR[closestFullPal][n] = 0
                tileEMergePalG[closestFullPal][n] = 0
                tileEMergePalB[closestFullPal][n] = 0
            
                for p in range(tileEMergePalNumTiles[closestFullPal]):
                    tileHi = tileEMergePalTileList[closestFullPal][p][0]
                    tileLo = tileEMergePalTileList[closestFullPal][p][1]
                        
                    for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                        if tileUniqueClrsPalClr[tileHi][tileLo][m] == n:
                            tileEMergePalR[closestFullPal][n] = tileEMergePalR[closestFullPal][n] + (tileUniqueClrsR[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                            tileEMergePalG[closestFullPal][n] = tileEMergePalG[closestFullPal][n] + (tileUniqueClrsG[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                            tileEMergePalB[closestFullPal][n] = tileEMergePalB[closestFullPal][n] + (tileUniqueClrsB[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
            
                #print("attempting divide of: {} / {}".format(tileEMergePalR[closestFullPal][n], tileEMergePalNumPix[closestFullPal][n]))
                tileEMergePalR[closestFullPal][n] = tileEMergePalR[closestFullPal][n] / tileEMergePalNumPix[closestFullPal][n]
                tileEMergePalG[closestFullPal][n] = tileEMergePalG[closestFullPal][n] / tileEMergePalNumPix[closestFullPal][n]
                tileEMergePalB[closestFullPal][n] = tileEMergePalB[closestFullPal][n] / tileEMergePalNumPix[closestFullPal][n]

            if not qLoop == 0:                    
                if avgClrDistance > prevAvgClrDistance:
                    gettingWorseCounter = gettingWorseCounter + 1
                else:
                    gettingWorseCounter = 0
                if avgClrDistance == prevAvgClrDistance:
                    convergCounter = convergCounter + 1
                else:
                    convergCounter = 0
                if convergCounter > 2 or gettingWorseCounter > 3:
                    if reshuffleAttempts > 5:
                        break
                    else:
                        #print("Reshuffle!")
                        gettingWorseCounter = 0
                        convergCounter = 0
                        reshuffleAttempts = reshuffleAttempts + 1

                        #merge two closest centroids...

                        mergeSumClosest = 999999
                        for n in range(15):
                            for m in range(n):
                                #removed a math.sqrt here
                                mergeSum = ((tileEMergePalR[closestFullPal][n] - tileEMergePalR[closestFullPal][m]) ** 2) + ((tileEMergePalG[closestFullPal][n] - tileEMergePalG[closestFullPal][m]) ** 2) + ((tileEMergePalB[closestFullPal][n] - tileEMergePalB[closestFullPal][m]) ** 2)
                                if mergeSum < mergeSumClosest:
                                    mergeSumClosest = mergeSum
                                    mergeSumIndexA = m
                                    mergeSumIndexB = n

                        #replace first centroid with average of two being merged
                        tileEMergePalR[closestFullPal][mergeSumIndexA] = (tileEMergePalR[closestFullPal][mergeSumIndexA] + tileEMergePalR[closestFullPal][mergeSumIndexB]) / 2
                        tileEMergePalG[closestFullPal][mergeSumIndexA] = (tileEMergePalG[closestFullPal][mergeSumIndexA] + tileEMergePalG[closestFullPal][mergeSumIndexB]) / 2
                        tileEMergePalB[closestFullPal][mergeSumIndexA] = (tileEMergePalB[closestFullPal][mergeSumIndexA] + tileEMergePalB[closestFullPal][mergeSumIndexB]) / 2

                        #replace second centroid with most distant point of most populated (with colors not pixels) cluster
                        splitDist = 0
                        mergeSumIndexA = 0    #we can reuse IndexA now since it's done

                        for n in range(15):
                            if tileEMergePalNumClrs[closestFullPal][n] > splitDist:
                                splitDist = tileEMergePalNumClrs[closestFullPal][n]
                                mergeSumIndexA = n

                        splitDist = 0
                        splitIndex = 0
                        for p in range(tileEMergePalNumTiles[closestFullPal]):
                            tileHi = tileEMergePalTileList[closestFullPal][p][0]
                            tileLo = tileEMergePalTileList[closestFullPal][p][1]
                            
                            for n in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                if tileUniqueClrsPalClr[tileHi][tileLo][n] == mergeSumIndexA:
                                    if tileUniqueClrsPalDist[tileHi][tileLo][n] > splitDist:
                                        splitDist = tileUniqueClrsPalDist[tileHi][tileLo][n]
                                        splitIndex = n

                        tileEMergePalR[closestFullPal][mergeSumIndexB] = tileUniqueClrsR[tileHi][tileLo][splitIndex]
                        tileEMergePalG[closestFullPal][mergeSumIndexB] = tileUniqueClrsG[tileHi][tileLo][splitIndex]
                        tileEMergePalR[closestFullPal][mergeSumIndexB] = tileUniqueClrsB[tileHi][tileLo][splitIndex]
                        
    #done quantizing, copy the mergeBestPal to the actual MergePal
    for n in range(15):
        tileEMergePalR[closestFullPal][n] = tileEMergeBestPalR[n]
        tileEMergePalG[closestFullPal][n] = tileEMergeBestPalG[n]
        tileEMergePalB[closestFullPal][n] = tileEMergeBestPalB[n]
        tileEMergePalNumPix[closestFullPal][n] = tileEMergeBestPalNumPix[n]
        tileEMergePalNumClrs[closestFullPal][n] = tileEMergeBestPalNumClrs[n]
    tileEMergePalAvg[closestFullPal] = bestAvgClrDistance
    
    #When we're done merging all empties, the list of full palettes BECOMES the new list!

#=======================================================================================================================
#so, create a NEW palette list by just copying over the data again?  Easier than trying to "cut" things
print("Shuffling Data Again...")

for i in range(fullPals):
    x = fullPalList[i]

    tileMergePalAvg[i] = tileEMergePalAvg[x]
    #tileMergePalRMS[i] = tileEMergePalRMS[x]
    tileMergePalNumTiles[i] = tileEMergePalNumTiles[x]
    
    for n in range(numPalettes):
        tileMergePalTileList[i][n][0] = tileEMergePalTileList[x][n][0]
        tileMergePalTileList[i][n][1] = tileEMergePalTileList[x][n][1]

    for n in range(15):
        tileMergePalR[i][n] = tileEMergePalR[x][n]
        tileMergePalG[i][n] = tileEMergePalG[x][n]
        tileMergePalB[i][n] = tileEMergePalB[x][n]
        tileMergePalNumPix[i][n] = tileEMergePalNumPix[x][n]
        tileMergePalNumClrs[i][n] = tileEMergePalNumClrs[x][n]

#=======================================================================================================================
#Dump a quick bitmap to confirm it worked so far
#
#print("Exporting Bitmap With Unfull Palettes Eliminated...")
#
#with open(outputBMPNameB, "wb") as f:
#
#    #Copy original header back verbatim
#    for i in range(pixelStartAddress):
#        f.write(bytelist[i])
#
#    #Then write new pixel data
#    for i in range(bitmapHeight):
#        for j in range(bitmapWidth):
#            tileCoordY = i%8
#            tileCoordX = j%8
#            mapCoordY = i//8
#            mapCoordX = j//8

            #for each pixel, lookup which palette to use (FIND mapCoordY, mapCoordX IN tileMergePalTileList), find the closest colour match in that palette, then write that colour value
            
#            foundTileMatch = False
#            for n in range(fullPals):
#                for m in range(tileMergePalNumTiles[n]):
#                    if tileMergePalTileList[n][m][0] == mapCoordY and tileMergePalTileList[n][m][1] == mapCoordX:
#                        foundTileMatch = True
#                        correctDrawPal = n
#                        break
#                if foundTileMatch == True:
#                    break

#            if foundTileMatch == False:
#                print("WTF Tile not found")
#                quit()

#            bestPixelDistance = 999999
#            for n in range(15):
#                pixelDistance = ((tileMergePalR[correctDrawPal][n] - tileClrsR[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)
#                pixelDistance = pixelDistance + ((tileMergePalG[correctDrawPal][n] - tileClrsG[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)
#                pixelDistance = pixelDistance + ((tileMergePalB[correctDrawPal][n] - tileClrsB[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)

#                if pixelDistance < bestPixelDistance:
#                    bestPixelDistance = pixelDistance
#                    bestClrMatch = n
                    
#            f.write(struct.pack("B", int(tileMergePalB[correctDrawPal][bestClrMatch] * 8)))
#            f.write(struct.pack("B", int(tileMergePalG[correctDrawPal][bestClrMatch] * 8)))
#            f.write(struct.pack("B", int(tileMergePalR[correctDrawPal][bestClrMatch] * 8)))

#=======================================================================================================================
#Do a quick crunch - only compare chunkSize palettes together before merging one.  Let the scan wrap around -
#hopefully blur out any pattern that would be caused by this segregation

print("Beginning Quick Palette Crunch")
numCrunches = fullPals - chunkSize
if numCrunches < 0:
    numCrunches = 0

crunch = 0
chunkCounter = chunkSize
bestMergeLoss = 999999
while crunch < numCrunches:
    jOffset = 0
    w = 0
    while w < fullPals:
        print("comparing palette {} / {}...  {} removed".format(w, (fullPals - 1), crunch))
        chunkCounter = chunkCounter - 1
        zRange = w - jOffset
        if zRange < 0:
            zRange = zRange + fullPals
        for z in range(zRange):
            j = z + jOffset
            if j >= fullPals:
                j = j - fullPals
            #assign each colour to an entry in the OTHER palette
            totalMergePaletteDistance = 0

            for n in range(tileMergePalNumTiles[w]):
                tileHi = tileMergePalTileList[w][n][0]
                tileLo = tileMergePalTileList[w][n][1]

                for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                    shortestDistance = 0

                    for k in range(15):
                        #removed a math.sqrt here
                        sumDistance[k] = ((tileMergePalR[j][k] - tileUniqueClrsR[tileHi][tileLo][m]) ** 2) + ((tileMergePalG[j][k] - tileUniqueClrsG[tileHi][tileLo][m]) ** 2) + ((tileMergePalB[j][k] - tileUniqueClrsB[tileHi][tileLo][m]) ** 2)

                        if k != 0:
                            if sumDistance[k] < sumDistance[shortestDistance]:
                                shortestDistance = k
                    
                    tileUniqueClrsPalClr[tileHi][tileLo][m] = shortestDistance
                    tileUniqueClrsPalDist[tileHi][tileLo][m] = sumDistance[shortestDistance]

                    totalMergePaletteDistance = totalMergePaletteDistance + (sumDistance[shortestDistance] * tileUniqueClrsNumPix[tileHi][tileLo][m])

            for n in range(tileMergePalNumTiles[j]):
                tileHi = tileMergePalTileList[j][n][0]
                tileLo = tileMergePalTileList[j][n][1]

                for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                    shortestDistance = 0

                    for k in range(15):
                        #removed a math.sqrt here
                        sumDistance[k] = ((tileMergePalR[w][k] - tileUniqueClrsR[tileHi][tileLo][m]) ** 2) + ((tileMergePalG[w][k] - tileUniqueClrsG[tileHi][tileLo][m]) ** 2) + ((tileMergePalB[w][k] - tileUniqueClrsB[tileHi][tileLo][m]) ** 2)

                        if k != 0:
                            if sumDistance[k] < sumDistance[shortestDistance]:
                                shortestDistance = k
                    
                    tileUniqueClrsPalClr[tileHi][tileLo][m] = shortestDistance
                    tileUniqueClrsPalDist[tileHi][tileLo][m] = sumDistance[shortestDistance]

                    totalMergePaletteDistance = totalMergePaletteDistance + (sumDistance[shortestDistance] * tileUniqueClrsNumPix[tileHi][tileLo][m])

            totalMergePaletteDistance = totalMergePaletteDistance / ((tileMergePalNumTiles[w] + tileMergePalNumTiles[j]) * 64)
            totalMergePaletteDistanceOLD = (tileMergePalAvg[w] + tileMergePalAvg[j]) / 2

            mergeLoss = (totalMergePaletteDistance - totalMergePaletteDistanceOLD) * (tileMergePalNumTiles[w] + tileMergePalNumTiles[j])    #losses weighted by number of tiles affected

            if mergeLoss < bestMergeLoss:
                print("New Best Merge Found!  {} and {} for {}".format(w, j, mergeLoss))
                bestMergeLoss = mergeLoss
                bestMergeIndexA = w
                bestMergeIndexB = j

        if chunkCounter == 0:
            #Now that we have indexes of the two palettes to merge, quantize a new palette for their combined set of tiles
            i = bestMergeIndexA
            j = bestMergeIndexB
            
            print("Merging {} into {} and Quantizing".format(i, j))
            for n in range(tileMergePalNumTiles[i]):
                tileMergePalTileList[j][tileMergePalNumTiles[j] + n][0] = tileMergePalTileList[i][n][0]
                tileMergePalTileList[j][tileMergePalNumTiles[j] + n][1] = tileMergePalTileList[i][n][1]
            tileMergePalNumTiles[j] = tileMergePalNumTiles[j] + tileMergePalNumTiles[i]

            #FULLY QUANTIZE the merged palette EVERY TIME.  Get random start point from palette's tiles
            bestAvgClrDistance = 999999
            #bestRMSClrDistance = 999999
            for k in range(trials):
                reshuffleAttempts = 0
                gettingWorseCounter = 0
                avgClrDistance = 999999
                prevAvgClrDistance = 999999
               
                n = 0
                while n < 15:
                    randomIndex = random.randint(0, tileMergePalNumTiles[j] - 1)
                    tileHi = tileMergePalTileList[j][randomIndex][0]
                    tileLo = tileMergePalTileList[j][randomIndex][1]
                
                    randomIndex = random.randint(0, (tileClrsNumUniqueClrs[tileHi][tileLo]-1)) #Inclusive
                    tileMergePalR[j][n] = tileUniqueClrsR[tileHi][tileLo][randomIndex]
                    tileMergePalG[j][n] = tileUniqueClrsG[tileHi][tileLo][randomIndex]
                    tileMergePalB[j][n] = tileUniqueClrsB[tileHi][tileLo][randomIndex]

                    reroll = False
                    for m in range(n):
                        if tileMergePalR[j][n] == prevClrs[m][0] and tileMergePalG[j][n] == prevClrs[m][1] and tileMergePalB[j][n] == prevClrs[m][2]:
                            reroll = True
                            break
                        
                    if reroll == False:
                        if n < 14:
                            prevClrs[n][0] = tileMergePalR[j][n]
                            prevClrs[n][1] = tileMergePalG[j][n]
                            prevClrs[n][2] = tileMergePalB[j][n]
                        n = n + 1

                #now quantize it!
                convergCounter = 0
                for qLoop in range(qLoops):
                    #print("{} Trial: {}  Loop: {},  avg{}  prev{}".format(i, k, qLoop, avgClrDistance, prevAvgClrDistance))
            
                    prevAvgClrDistance = avgClrDistance
            
                    paletteReady = False
                    while paletteReady == False:
                        for n in range(15):
                            tileMergePalNumPix[j][n] = 0
                            tileMergePalNumClrs[j][n] = 0

                        avgClrDistance = 0
                        #RMSClrDistance = 0

                        #find each colour's closest palette colour and store distance
                        for p in range(tileMergePalNumTiles[j]):
                            tileHi = tileMergePalTileList[j][p][0]
                            tileLo = tileMergePalTileList[j][p][1]
                        
                            for n in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                closestPixelDistance = 999999
                                for m in range(15):
                                    pixelDistance = ((tileUniqueClrsR[tileHi][tileLo][n] - tileMergePalR[j][m]) ** 2) + ((tileUniqueClrsG[tileHi][tileLo][n] - tileMergePalG[j][m]) ** 2) + ((tileUniqueClrsB[tileHi][tileLo][n] - tileMergePalB[j][m]) ** 2)
                                    #pixelDistance = math.sqrt(pixelDistance)
                                    if pixelDistance < closestPixelDistance:
                                        closestPixelDistance = pixelDistance
                                        closestPixelColour = m
                                tileUniqueClrsPalClr[tileHi][tileLo][n] = closestPixelColour
                                tileUniqueClrsPalDist[tileHi][tileLo][n] = closestPixelDistance

                                tileMergePalNumPix[j][closestPixelColour] = tileMergePalNumPix[j][closestPixelColour] + tileUniqueClrsNumPix[tileHi][tileLo][n]         
                                tileMergePalNumClrs[j][closestPixelColour] = tileMergePalNumClrs[j][closestPixelColour] + 1
                            
                                avgClrDistance = avgClrDistance + (closestPixelDistance * tileUniqueClrsNumPix[tileHi][tileLo][n])
                                #RMSClrDistance = RMSClrDistance + ((closestPixelDistance * closestPixelDistance) * tileUniqueClrsNumPix[tileHi][tileLo][n])

                        #Check if any palette colours are unused.  If so replace it with the most distant colour
                        #if so reassign colour to most distant and recalculate.  There will ALWAYS be enough colours to fill a palette here.
                        paletteReady = True
                        for n in range(15):
                            if tileMergePalNumPix[j][n] == 0:
                                paletteReady = False
                                #print("omgpalettenotready - {}, {}".format(tileMergePalNumPix[j][n], n))
        
                                mostClrDistance = 0
                                mostDistantClr = 0
                                for p in range(tileMergePalNumTiles[j]):
                                    tileHi = tileMergePalTileList[j][p][0]
                                    tileLo = tileMergePalTileList[j][p][1]
                                    
                                    for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                        if tileUniqueClrsPalDist[tileHi][tileLo][m] > mostClrDistance:
                                            mostClrDistance = tileUniqueClrsPalDist[tileHi][tileLo][m]
                                            mostDistantClr = m
                                            mostDistantTileHi = tileHi
                                            mostDistantTileLo = tileLo
                                            
                                tileMergePalR[j][n] = tileUniqueClrsR[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                                tileMergePalG[j][n] = tileUniqueClrsG[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                                tileMergePalB[j][n] = tileUniqueClrsB[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                                    
                    avgClrDistance = (avgClrDistance/(tileMergePalNumTiles[j]*64))
                    #RMSClrDistance = math.sqrt(RMSClrDistance/(tileMergePalNumTiles[j]*64))

                    if avgClrDistance < bestAvgClrDistance:
                        #we have a new best!  Store the palette
                        print("Quantizing - New Best Found!  {}".format(avgClrDistance))
                        for n in range(15):
                            tileEMergeBestPalR[n] = tileMergePalR[j][n]
                            tileEMergeBestPalG[n] = tileMergePalG[j][n]
                            tileEMergeBestPalB[n] = tileMergePalB[j][n]
                            tileEMergeBestPalNumPix[n] = tileMergePalNumPix[j][n]
                            tileEMergeBestPalNumClrs[n] = tileMergePalNumClrs[j][n]
                        bestAvgClrDistance = avgClrDistance
                        #bestRMSClrDistance = RMSClrDistance
                                
                    #calculate new palette colours
                    for n in range(15):
                        tileMergePalR[j][n] = 0
                        tileMergePalG[j][n] = 0
                        tileMergePalB[j][n] = 0
                        
                        for p in range(tileMergePalNumTiles[j]):
                            tileHi = tileMergePalTileList[j][p][0]
                            tileLo = tileMergePalTileList[j][p][1]
                            
                            for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                if tileUniqueClrsPalClr[tileHi][tileLo][m] == n:
                                    tileMergePalR[j][n] = tileMergePalR[j][n] + (tileUniqueClrsR[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                                    tileMergePalG[j][n] = tileMergePalG[j][n] + (tileUniqueClrsG[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                                    tileMergePalB[j][n] = tileMergePalB[j][n] + (tileUniqueClrsB[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                
                        #print("attempting divide of: {} / {}".format(tileMergePalR[j][n], tileMergePalNumPix[j][n]))
                        tileMergePalR[j][n] = tileMergePalR[j][n] / tileMergePalNumPix[j][n]
                        tileMergePalG[j][n] = tileMergePalG[j][n] / tileMergePalNumPix[j][n]
                        tileMergePalB[j][n] = tileMergePalB[j][n] / tileMergePalNumPix[j][n]

                    if not qLoop == 0:                    
                        if avgClrDistance > prevAvgClrDistance:
                            gettingWorseCounter = gettingWorseCounter + 1
                        else:
                            gettingWorseCounter = 0
                        if avgClrDistance == prevAvgClrDistance:
                            convergCounter = convergCounter + 1
                        else:
                            convergCounter = 0
                        if convergCounter > 2 or gettingWorseCounter > 3:
                            if reshuffleAttempts > 5:
                                break
                            else:
                                #print("Reshuffle!")
                                gettingWorseCounter = 0
                                convergCounter = 0
                                reshuffleAttempts = reshuffleAttempts + 1
            
                                #merge two closest centroids...
            
                                mergeSumClosest = 999999
                                for n in range(15):
                                    for m in range(n):
                                        #removed a math.sqrt here
                                        mergeSum = ((tileMergePalR[j][n] - tileMergePalR[j][m]) ** 2) + ((tileMergePalG[j][n] - tileMergePalG[j][m]) ** 2) + ((tileMergePalB[j][n] - tileMergePalB[j][m]) ** 2)
                                        if mergeSum < mergeSumClosest:
                                            mergeSumClosest = mergeSum
                                            mergeSumIndexA = m
                                            mergeSumIndexB = n

                                #replace first centroid with average of two being merged
                                tileMergePalR[j][mergeSumIndexA] = (tileMergePalR[j][mergeSumIndexA] + tileMergePalR[j][mergeSumIndexB]) / 2
                                tileMergePalG[j][mergeSumIndexA] = (tileMergePalG[j][mergeSumIndexA] + tileMergePalG[j][mergeSumIndexB]) / 2
                                tileMergePalB[j][mergeSumIndexA] = (tileMergePalB[j][mergeSumIndexA] + tileMergePalB[j][mergeSumIndexB]) / 2

                                #replace second centroid with most distant point of most populated (with colors not pixels) cluster
                                splitDist = 0
                                mergeSumIndexA = 0    #we can reuse IndexA now since it's done

                                for n in range(15):
                                    if tileMergePalNumClrs[j][n] > splitDist:
                                        splitDist = tileMergePalNumClrs[j][n]
                                        mergeSumIndexA = n

                                splitDist = 0
                                splitIndex = 0
                                for p in range(tileMergePalNumTiles[j]):
                                    tileHi = tileMergePalTileList[j][p][0]
                                    tileLo = tileMergePalTileList[j][p][1]
                                
                                    for n in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                        if tileUniqueClrsPalClr[tileHi][tileLo][n] == mergeSumIndexA:
                                            if tileUniqueClrsPalDist[tileHi][tileLo][n] > splitDist:
                                                splitDist = tileUniqueClrsPalDist[tileHi][tileLo][n]
                                                splitIndex = n

                                tileMergePalR[j][mergeSumIndexB] = tileUniqueClrsR[tileHi][tileLo][splitIndex]
                                tileMergePalG[j][mergeSumIndexB] = tileUniqueClrsG[tileHi][tileLo][splitIndex]
                                tileMergePalR[j][mergeSumIndexB] = tileUniqueClrsB[tileHi][tileLo][splitIndex]
                            
            #done quantizing, copy the mergeBestPal to the actual MergePal
            for n in range(15):
                tileMergePalR[j][n] = tileEMergeBestPalR[n]
                tileMergePalG[j][n] = tileEMergeBestPalG[n]
                tileMergePalB[j][n] = tileEMergeBestPalB[n]
                tileMergePalNumPix[j][n] = tileEMergeBestPalNumPix[n]
                tileMergePalNumClrs[j][n] = tileEMergeBestPalNumClrs[n]
            tileMergePalAvg[j] = bestAvgClrDistance

            #NOW WE HAVE TO ELIMINATE PALETTE i.  Starting at that address, SHIFT every entry back by one index, then decrement fullpals
            #i goes from 0 to fullPals - 1.  If i is at max value, we want to SKIP this loop ALTOGETHER.  So, minus one so that (fullPals - (fullPals - 1) - 1) = 0.

            for n in range((fullPals - i) - 1):
                for m in range(15):
                    tileMergePalR[i + n][m] = tileMergePalR[i + n + 1][m]
                    tileMergePalG[i + n][m] = tileMergePalG[i + n + 1][m]
                    tileMergePalB[i + n][m] = tileMergePalB[i + n + 1][m]
                    tileMergePalNumPix[i + n][m] = tileMergePalNumPix[i + n + 1][m]
                    tileMergePalNumClrs[i + n][m] = tileMergePalNumClrs[i + n + 1][m]
                tileMergePalAvg[i + n] = tileMergePalAvg[i + n + 1]
            
                for k in range(tileMergePalNumTiles[i + n + 1]):
                    tileMergePalTileList[i + n][k][0] = tileMergePalTileList[i + n + 1][k][0]
                    tileMergePalTileList[i + n][k][1] = tileMergePalTileList[i + n + 1][k][1]
                tileMergePalNumTiles[i + n] = tileMergePalNumTiles[i + n + 1]
                    
            fullPals = fullPals - 1
            jOffset = w
            chunkCounter = chunkSize
            crunch = crunch + 1
            bestMergeLoss = 999999

        w = w + 1

#=======================================================================================================================
#now crunch the remaining palettes the standard way

print("Beginning Standard Palette Crunch")
numCrunches = fullPals - targetNumPalettes
         
for crunch in range(numCrunches):
    bestMergeLoss = 999999

    for i in range(fullPals):
        print("comparing palette {} / {}...  {} removed".format(i, (fullPals - 1), crunch))
        for j in range(i):
            #assign each colour to an entry in the OTHER palette
            totalMergePaletteDistance = 0

            for n in range(tileMergePalNumTiles[i]):
                tileHi = tileMergePalTileList[i][n][0]
                tileLo = tileMergePalTileList[i][n][1]

                for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                    shortestDistance = 0

                    for k in range(15):
                        #removed a math.sqrt here
                        sumDistance[k] = ((tileMergePalR[j][k] - tileUniqueClrsR[tileHi][tileLo][m]) ** 2) + ((tileMergePalG[j][k] - tileUniqueClrsG[tileHi][tileLo][m]) ** 2) + ((tileMergePalB[j][k] - tileUniqueClrsB[tileHi][tileLo][m]) ** 2)

                        if k != 0:
                            if sumDistance[k] < sumDistance[shortestDistance]:
                                shortestDistance = k
                    
                    tileUniqueClrsPalClr[tileHi][tileLo][m] = shortestDistance
                    tileUniqueClrsPalDist[tileHi][tileLo][m] = sumDistance[shortestDistance]

                    totalMergePaletteDistance = totalMergePaletteDistance + (sumDistance[shortestDistance] * tileUniqueClrsNumPix[tileHi][tileLo][m])

            for n in range(tileMergePalNumTiles[j]):
                tileHi = tileMergePalTileList[j][n][0]
                tileLo = tileMergePalTileList[j][n][1]

                for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                    shortestDistance = 0

                    for k in range(15):
                        #removed a math.sqrt here
                        sumDistance[k] = ((tileMergePalR[i][k] - tileUniqueClrsR[tileHi][tileLo][m]) ** 2) + ((tileMergePalG[i][k] - tileUniqueClrsG[tileHi][tileLo][m]) ** 2) + ((tileMergePalB[i][k] - tileUniqueClrsB[tileHi][tileLo][m]) ** 2)

                        if k != 0:
                            if sumDistance[k] < sumDistance[shortestDistance]:
                                shortestDistance = k
                    
                    tileUniqueClrsPalClr[tileHi][tileLo][m] = shortestDistance
                    tileUniqueClrsPalDist[tileHi][tileLo][m] = sumDistance[shortestDistance]

                    totalMergePaletteDistance = totalMergePaletteDistance + (sumDistance[shortestDistance] * tileUniqueClrsNumPix[tileHi][tileLo][m])

            totalMergePaletteDistance = totalMergePaletteDistance / ((tileMergePalNumTiles[i] + tileMergePalNumTiles[j]) * 64)
            totalMergePaletteDistanceOLD = (tileMergePalAvg[i] + tileMergePalAvg[j]) / 2

            mergeLoss = (totalMergePaletteDistance - totalMergePaletteDistanceOLD) * (tileMergePalNumTiles[i] + tileMergePalNumTiles[j])    #losses weighted by number of tiles affected

            if mergeLoss < bestMergeLoss:
                print("New Best Merge Found!  {} and {} for {}".format(i, j, mergeLoss))
                bestMergeLoss = mergeLoss
                bestMergeIndexA = i
                bestMergeIndexB = j

    #Now that we have indexes of the two palettes to merge, quantize a new palette for their combined set of tiles
    i = bestMergeIndexA
    j = bestMergeIndexB

    print("Merging {} into {} and Quantizing".format(i, j))
    for n in range(tileMergePalNumTiles[i]):
        tileMergePalTileList[j][tileMergePalNumTiles[j] + n][0] = tileMergePalTileList[i][n][0]
        tileMergePalTileList[j][tileMergePalNumTiles[j] + n][1] = tileMergePalTileList[i][n][1]
    tileMergePalNumTiles[j] = tileMergePalNumTiles[j] + tileMergePalNumTiles[i]

    #FULLY QUANTIZE the merged palette EVERY TIME.  Get random start point from palette's tiles
    bestAvgClrDistance = 999999
    #bestRMSClrDistance = 999999
    for k in range(trials):
        reshuffleAttempts = 0
        gettingWorseCounter = 0
        avgClrDistance = 999999
        prevAvgClrDistance = 999999
           
        n = 0
        while n < 15:
            randomIndex = random.randint(0, tileMergePalNumTiles[j] - 1)
            tileHi = tileMergePalTileList[j][randomIndex][0]
            tileLo = tileMergePalTileList[j][randomIndex][1]
            
            randomIndex = random.randint(0, (tileClrsNumUniqueClrs[tileHi][tileLo]-1)) #Inclusive
            tileMergePalR[j][n] = tileUniqueClrsR[tileHi][tileLo][randomIndex]
            tileMergePalG[j][n] = tileUniqueClrsG[tileHi][tileLo][randomIndex]
            tileMergePalB[j][n] = tileUniqueClrsB[tileHi][tileLo][randomIndex]

            reroll = False
            for m in range(n):
                if tileMergePalR[j][n] == prevClrs[m][0] and tileMergePalG[j][n] == prevClrs[m][1] and tileMergePalB[j][n] == prevClrs[m][2]:
                    reroll = True
                    break
                    
            if reroll == False:
                if n < 14:
                    prevClrs[n][0] = tileMergePalR[j][n]
                    prevClrs[n][1] = tileMergePalG[j][n]
                    prevClrs[n][2] = tileMergePalB[j][n]
                n = n + 1

        #now quantize it!
        convergCounter = 0
        for qLoop in range(qLoops):
            #print("{} Trial: {}  Loop: {},  avg{}  prev{}".format(i, k, qLoop, avgClrDistance, prevAvgClrDistance))

            prevAvgClrDistance = avgClrDistance

            paletteReady = False
            while paletteReady == False:
                for n in range(15):
                    tileMergePalNumPix[j][n] = 0
                    tileMergePalNumClrs[j][n] = 0

                avgClrDistance = 0
                #RMSClrDistance = 0

                #find each colour's closest palette colour and store distance
                for p in range(tileMergePalNumTiles[j]):
                    tileHi = tileMergePalTileList[j][p][0]
                    tileLo = tileMergePalTileList[j][p][1]
                    
                    for n in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                        closestPixelDistance = 999999
                        for m in range(15):
                            pixelDistance = ((tileUniqueClrsR[tileHi][tileLo][n] - tileMergePalR[j][m]) ** 2) + ((tileUniqueClrsG[tileHi][tileLo][n] - tileMergePalG[j][m]) ** 2) + ((tileUniqueClrsB[tileHi][tileLo][n] - tileMergePalB[j][m]) ** 2)
                            #pixelDistance = math.sqrt(pixelDistance)
                            if pixelDistance < closestPixelDistance:
                                closestPixelDistance = pixelDistance
                                closestPixelColour = m
                        tileUniqueClrsPalClr[tileHi][tileLo][n] = closestPixelColour
                        tileUniqueClrsPalDist[tileHi][tileLo][n] = closestPixelDistance

                        tileMergePalNumPix[j][closestPixelColour] = tileMergePalNumPix[j][closestPixelColour] + tileUniqueClrsNumPix[tileHi][tileLo][n]         
                        tileMergePalNumClrs[j][closestPixelColour] = tileMergePalNumClrs[j][closestPixelColour] + 1
                        
                        avgClrDistance = avgClrDistance + (closestPixelDistance * tileUniqueClrsNumPix[tileHi][tileLo][n])
                        #RMSClrDistance = RMSClrDistance + ((closestPixelDistance * closestPixelDistance) * tileUniqueClrsNumPix[tileHi][tileLo][n])

                #Check if any palette colours are unused.  If so replace it with the most distant colour
                #if so reassign colour to most distant and recalculate.  There will ALWAYS be enough colours to fill a palette here.
                paletteReady = True
                for n in range(15):
                    if tileMergePalNumPix[j][n] == 0:
                        paletteReady = False
                        #print("omgpalettenotready - {}, {}".format(tileMergePalNumPix[j][n], n))
    
                        mostClrDistance = 0
                        mostDistantClr = 0
                        for p in range(tileMergePalNumTiles[j]):
                            tileHi = tileMergePalTileList[j][p][0]
                            tileLo = tileMergePalTileList[j][p][1]
                                
                            for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                if tileUniqueClrsPalDist[tileHi][tileLo][m] > mostClrDistance:
                                    mostClrDistance = tileUniqueClrsPalDist[tileHi][tileLo][m]
                                    mostDistantClr = m
                                    mostDistantTileHi = tileHi
                                    mostDistantTileLo = tileLo
                                        
                        tileMergePalR[j][n] = tileUniqueClrsR[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                        tileMergePalG[j][n] = tileUniqueClrsG[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                        tileMergePalB[j][n] = tileUniqueClrsB[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                                
            avgClrDistance = (avgClrDistance/(tileMergePalNumTiles[j]*64))
            #RMSClrDistance = math.sqrt(RMSClrDistance/(tileMergePalNumTiles[j]*64))

            if avgClrDistance < bestAvgClrDistance:
                #we have a new best!  Store the palette
                print("Quantizing - New Best Found!  {}".format(avgClrDistance))
                for n in range(15):
                    tileEMergeBestPalR[n] = tileMergePalR[j][n]
                    tileEMergeBestPalG[n] = tileMergePalG[j][n]
                    tileEMergeBestPalB[n] = tileMergePalB[j][n]
                    tileEMergeBestPalNumPix[n] = tileMergePalNumPix[j][n]
                    tileEMergeBestPalNumClrs[n] = tileMergePalNumClrs[j][n]
                bestAvgClrDistance = avgClrDistance
                #bestRMSClrDistance = RMSClrDistance
                            
            #calculate new palette colours
            for n in range(15):
                tileMergePalR[j][n] = 0
                tileMergePalG[j][n] = 0
                tileMergePalB[j][n] = 0
            
                for p in range(tileMergePalNumTiles[j]):
                    tileHi = tileMergePalTileList[j][p][0]
                    tileLo = tileMergePalTileList[j][p][1]
                        
                    for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                        if tileUniqueClrsPalClr[tileHi][tileLo][m] == n:
                            tileMergePalR[j][n] = tileMergePalR[j][n] + (tileUniqueClrsR[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                            tileMergePalG[j][n] = tileMergePalG[j][n] + (tileUniqueClrsG[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                            tileMergePalB[j][n] = tileMergePalB[j][n] + (tileUniqueClrsB[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
            
                #print("attempting divide of: {} / {}".format(tileMergePalR[j][n], tileMergePalNumPix[j][n]))
                tileMergePalR[j][n] = tileMergePalR[j][n] / tileMergePalNumPix[j][n]
                tileMergePalG[j][n] = tileMergePalG[j][n] / tileMergePalNumPix[j][n]
                tileMergePalB[j][n] = tileMergePalB[j][n] / tileMergePalNumPix[j][n]

            if not qLoop == 0:                    
                if avgClrDistance > prevAvgClrDistance:
                    gettingWorseCounter = gettingWorseCounter + 1
                else:
                    gettingWorseCounter = 0
                if avgClrDistance == prevAvgClrDistance:
                    convergCounter = convergCounter + 1
                else:
                    convergCounter = 0
                if convergCounter > 2 or gettingWorseCounter > 3:
                    if reshuffleAttempts > 5:
                        break
                    else:
                        #print("Reshuffle!")
                        gettingWorseCounter = 0
                        convergCounter = 0
                        reshuffleAttempts = reshuffleAttempts + 1

                        #merge two closest centroids...

                        mergeSumClosest = 999999
                        for n in range(15):
                            for m in range(n):
                                #removed a math.sqrt here
                                mergeSum = ((tileMergePalR[j][n] - tileMergePalR[j][m]) ** 2) + ((tileMergePalG[j][n] - tileMergePalG[j][m]) ** 2) + ((tileMergePalB[j][n] - tileMergePalB[j][m]) ** 2)
                                if mergeSum < mergeSumClosest:
                                    mergeSumClosest = mergeSum
                                    mergeSumIndexA = m
                                    mergeSumIndexB = n

                        #replace first centroid with average of two being merged
                        tileMergePalR[j][mergeSumIndexA] = (tileMergePalR[j][mergeSumIndexA] + tileMergePalR[j][mergeSumIndexB]) / 2
                        tileMergePalG[j][mergeSumIndexA] = (tileMergePalG[j][mergeSumIndexA] + tileMergePalG[j][mergeSumIndexB]) / 2
                        tileMergePalB[j][mergeSumIndexA] = (tileMergePalB[j][mergeSumIndexA] + tileMergePalB[j][mergeSumIndexB]) / 2

                        #replace second centroid with most distant point of most populated (with colors not pixels) cluster
                        splitDist = 0
                        mergeSumIndexA = 0    #we can reuse IndexA now since it's done

                        for n in range(15):
                            if tileMergePalNumClrs[j][n] > splitDist:
                                splitDist = tileMergePalNumClrs[j][n]
                                mergeSumIndexA = n

                        splitDist = 0
                        splitIndex = 0
                        for p in range(tileMergePalNumTiles[j]):
                            tileHi = tileMergePalTileList[j][p][0]
                            tileLo = tileMergePalTileList[j][p][1]
                            
                            for n in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                if tileUniqueClrsPalClr[tileHi][tileLo][n] == mergeSumIndexA:
                                    if tileUniqueClrsPalDist[tileHi][tileLo][n] > splitDist:
                                        splitDist = tileUniqueClrsPalDist[tileHi][tileLo][n]
                                        splitIndex = n

                        tileMergePalR[j][mergeSumIndexB] = tileUniqueClrsR[tileHi][tileLo][splitIndex]
                        tileMergePalG[j][mergeSumIndexB] = tileUniqueClrsG[tileHi][tileLo][splitIndex]
                        tileMergePalR[j][mergeSumIndexB] = tileUniqueClrsB[tileHi][tileLo][splitIndex]
                        
    #done quantizing, copy the mergeBestPal to the actual MergePal
    for n in range(15):
        tileMergePalR[j][n] = tileEMergeBestPalR[n]
        tileMergePalG[j][n] = tileEMergeBestPalG[n]
        tileMergePalB[j][n] = tileEMergeBestPalB[n]
        tileMergePalNumPix[j][n] = tileEMergeBestPalNumPix[n]
        tileMergePalNumClrs[j][n] = tileEMergeBestPalNumClrs[n]
    tileMergePalAvg[j] = bestAvgClrDistance

    #NOW WE HAVE TO ELIMINATE PALETTE i.  Starting at that address, SHIFT every entry back by one index, then decrement fullpals
    #i goes from 0 to fullPals - 1.  If i is at max value, we want to SKIP this loop ALTOGETHER.  So, minus one so that (fullPals - (fullPals - 1) - 1) = 0.

    for n in range((fullPals - i) - 1):
        for m in range(15):
            tileMergePalR[i + n][m] = tileMergePalR[i + n + 1][m]
            tileMergePalG[i + n][m] = tileMergePalG[i + n + 1][m]
            tileMergePalB[i + n][m] = tileMergePalB[i + n + 1][m]
            tileMergePalNumPix[i + n][m] = tileMergePalNumPix[i + n + 1][m]
            tileMergePalNumClrs[i + n][m] = tileMergePalNumClrs[i + n + 1][m]
        tileMergePalAvg[i + n] = tileMergePalAvg[i + n + 1]
        
        for k in range(tileMergePalNumTiles[i + n + 1]):
            tileMergePalTileList[i + n][k][0] = tileMergePalTileList[i + n + 1][k][0]
            tileMergePalTileList[i + n][k][1] = tileMergePalTileList[i + n + 1][k][1]
        tileMergePalNumTiles[i + n] = tileMergePalNumTiles[i + n + 1]
        
    fullPals = fullPals - 1


#=======================================================================================================================
#Run one final quantize on all palettes

print("Running xtraQuantize for {} extra trials!".format(xTrials))

for j in range(fullPals):
    for n in range(15):
        tileEMergeBestPalR[n] = tileMergePalR[j][n]
        tileEMergeBestPalG[n] = tileMergePalG[j][n]
        tileEMergeBestPalB[n] = tileMergePalB[j][n]
        tileEMergeBestPalNumPix[n] = tileMergePalNumPix[j][n]
        tileEMergeBestPalNumClrs[n] = tileMergePalNumClrs[j][n]
    bestAvgClrDistance = tileMergePalAvg[j]

    for k in range(xTrials):
        print("Palette {}, Trial {}...".format(j, k))
        reshuffleAttempts = 0
        gettingWorseCounter = 0
        avgClrDistance = 999999
        prevAvgClrDistance = 999999
           
        n = 0
        while n < 15:
            randomIndex = random.randint(0, tileMergePalNumTiles[j] - 1)
            tileHi = tileMergePalTileList[j][randomIndex][0]
            tileLo = tileMergePalTileList[j][randomIndex][1]
            
            randomIndex = random.randint(0, (tileClrsNumUniqueClrs[tileHi][tileLo]-1)) #Inclusive
            tileMergePalR[j][n] = tileUniqueClrsR[tileHi][tileLo][randomIndex]
            tileMergePalG[j][n] = tileUniqueClrsG[tileHi][tileLo][randomIndex]
            tileMergePalB[j][n] = tileUniqueClrsB[tileHi][tileLo][randomIndex]

            reroll = False
            for m in range(n):
                if tileMergePalR[j][n] == prevClrs[m][0] and tileMergePalG[j][n] == prevClrs[m][1] and tileMergePalB[j][n] == prevClrs[m][2]:
                    reroll = True
                    break
                    
            if reroll == False:
                if n < 14:
                    prevClrs[n][0] = tileMergePalR[j][n]
                    prevClrs[n][1] = tileMergePalG[j][n]
                    prevClrs[n][2] = tileMergePalB[j][n]
                n = n + 1

        #now quantize it!
        convergCounter = 0                
        for qLoop in range(qLoops):
            #print("{} Trial: {}  Loop: {},  avg{}  prev{}".format(i, k, qLoop, avgClrDistance, prevAvgClrDistance))

            prevAvgClrDistance = avgClrDistance

            paletteReady = False
            while paletteReady == False:
                for n in range(15):
                    tileMergePalNumPix[j][n] = 0
                    tileMergePalNumClrs[j][n] = 0

                avgClrDistance = 0
                #RMSClrDistance = 0

                #find each colour's closest palette colour and store distance
                for p in range(tileMergePalNumTiles[j]):
                    tileHi = tileMergePalTileList[j][p][0]
                    tileLo = tileMergePalTileList[j][p][1]
                    
                    for n in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                        closestPixelDistance = 999999
                        for m in range(15):
                            pixelDistance = ((tileUniqueClrsR[tileHi][tileLo][n] - tileMergePalR[j][m]) ** 2) + ((tileUniqueClrsG[tileHi][tileLo][n] - tileMergePalG[j][m]) ** 2) + ((tileUniqueClrsB[tileHi][tileLo][n] - tileMergePalB[j][m]) ** 2)
                            #pixelDistance = math.sqrt(pixelDistance)
                            if pixelDistance < closestPixelDistance:
                                closestPixelDistance = pixelDistance
                                closestPixelColour = m
                        tileUniqueClrsPalClr[tileHi][tileLo][n] = closestPixelColour
                        tileUniqueClrsPalDist[tileHi][tileLo][n] = closestPixelDistance

                        tileMergePalNumPix[j][closestPixelColour] = tileMergePalNumPix[j][closestPixelColour] + tileUniqueClrsNumPix[tileHi][tileLo][n]         
                        tileMergePalNumClrs[j][closestPixelColour] = tileMergePalNumClrs[j][closestPixelColour] + 1
                        
                        avgClrDistance = avgClrDistance + (closestPixelDistance * tileUniqueClrsNumPix[tileHi][tileLo][n])
                        #RMSClrDistance = RMSClrDistance + ((closestPixelDistance * closestPixelDistance) * tileUniqueClrsNumPix[tileHi][tileLo][n])

                #Check if any palette colours are unused.  If so replace it with the most distant colour
                #if so reassign colour to most distant and recalculate.  There will ALWAYS be enough colours to fill a palette here.
                paletteReady = True
                for n in range(15):
                    if tileMergePalNumPix[j][n] == 0:
                        paletteReady = False
                        #print("omgpalettenotready - {}, {}".format(tileMergePalNumPix[j][n], n))
    
                        mostClrDistance = 0
                        mostDistantClr = 0
                        for p in range(tileMergePalNumTiles[j]):
                            tileHi = tileMergePalTileList[j][p][0]
                            tileLo = tileMergePalTileList[j][p][1]
                                
                            for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                if tileUniqueClrsPalDist[tileHi][tileLo][m] > mostClrDistance:
                                    mostClrDistance = tileUniqueClrsPalDist[tileHi][tileLo][m]
                                    mostDistantClr = m
                                    mostDistantTileHi = tileHi
                                    mostDistantTileLo = tileLo
                                        
                        tileMergePalR[j][n] = tileUniqueClrsR[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                        tileMergePalG[j][n] = tileUniqueClrsG[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                        tileMergePalB[j][n] = tileUniqueClrsB[mostDistantTileHi][mostDistantTileLo][mostDistantClr]
                                
            avgClrDistance = (avgClrDistance/(tileMergePalNumTiles[j]*64))
            #RMSClrDistance = math.sqrt(RMSClrDistance/(tileMergePalNumTiles[j]*64))

            if avgClrDistance < bestAvgClrDistance:
                #we have a new best!  Store the palette
                print("xtraQuantize made an improvement! {} over {}".format(avgClrDistance, bestAvgClrDistance))
                for n in range(15):
                    tileEMergeBestPalR[n] = tileMergePalR[j][n]
                    tileEMergeBestPalG[n] = tileMergePalG[j][n]
                    tileEMergeBestPalB[n] = tileMergePalB[j][n]
                    tileEMergeBestPalNumPix[n] = tileMergePalNumPix[j][n]
                    tileEMergeBestPalNumClrs[n] = tileMergePalNumClrs[j][n]
                bestAvgClrDistance = avgClrDistance
                #bestRMSClrDistance = RMSClrDistance
                            
            #calculate new palette colours
            for n in range(15):
                tileMergePalR[j][n] = 0
                tileMergePalG[j][n] = 0
                tileMergePalB[j][n] = 0
            
                for p in range(tileMergePalNumTiles[j]):
                    tileHi = tileMergePalTileList[j][p][0]
                    tileLo = tileMergePalTileList[j][p][1]
                        
                    for m in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                        if tileUniqueClrsPalClr[tileHi][tileLo][m] == n:
                            tileMergePalR[j][n] = tileMergePalR[j][n] + (tileUniqueClrsR[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                            tileMergePalG[j][n] = tileMergePalG[j][n] + (tileUniqueClrsG[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
                            tileMergePalB[j][n] = tileMergePalB[j][n] + (tileUniqueClrsB[tileHi][tileLo][m] * tileUniqueClrsNumPix[tileHi][tileLo][m])
            
                #print("attempting divide of: {} / {}".format(tileMergePalR[j][n], tileMergePalNumPix[j][n]))
                tileMergePalR[j][n] = tileMergePalR[j][n] / tileMergePalNumPix[j][n]
                tileMergePalG[j][n] = tileMergePalG[j][n] / tileMergePalNumPix[j][n]
                tileMergePalB[j][n] = tileMergePalB[j][n] / tileMergePalNumPix[j][n]

            if not qLoop == 0:                    
                if avgClrDistance > prevAvgClrDistance:
                    gettingWorseCounter = gettingWorseCounter + 1
                else:
                    gettingWorseCounter = 0
                if avgClrDistance == prevAvgClrDistance:
                    convergCounter = convergCounter + 1
                else:
                    convergCounter = 0
                if convergCounter > 2 or gettingWorseCounter > 3:
                    if reshuffleAttempts > 5:
                        break
                    else:
                        #print("Reshuffle!")
                        gettingWorseCounter = 0
                        convergCounter = 0
                        reshuffleAttempts = reshuffleAttempts + 1

                        #merge two closest centroids...

                        mergeSumClosest = 999999
                        for n in range(15):
                            for m in range(n):
                                #removed a math.sqrt here
                                mergeSum = ((tileMergePalR[j][n] - tileMergePalR[j][m]) ** 2) + ((tileMergePalG[j][n] - tileMergePalG[j][m]) ** 2) + ((tileMergePalB[j][n] - tileMergePalB[j][m]) ** 2)
                                if mergeSum < mergeSumClosest:
                                    mergeSumClosest = mergeSum
                                    mergeSumIndexA = m
                                    mergeSumIndexB = n

                        #replace first centroid with average of two being merged
                        tileMergePalR[j][mergeSumIndexA] = (tileMergePalR[j][mergeSumIndexA] + tileMergePalR[j][mergeSumIndexB]) / 2
                        tileMergePalG[j][mergeSumIndexA] = (tileMergePalG[j][mergeSumIndexA] + tileMergePalG[j][mergeSumIndexB]) / 2
                        tileMergePalB[j][mergeSumIndexA] = (tileMergePalB[j][mergeSumIndexA] + tileMergePalB[j][mergeSumIndexB]) / 2

                        #replace second centroid with most distant point of most populated (with colors not pixels) cluster
                        splitDist = 0
                        mergeSumIndexA = 0    #we can reuse IndexA now since it's done

                        for n in range(15):
                            if tileMergePalNumClrs[j][n] > splitDist:
                                splitDist = tileMergePalNumClrs[j][n]
                                mergeSumIndexA = n

                        splitDist = 0
                        splitIndex = 0
                        for p in range(tileMergePalNumTiles[j]):
                            tileHi = tileMergePalTileList[j][p][0]
                            tileLo = tileMergePalTileList[j][p][1]
                            
                            for n in range(tileClrsNumUniqueClrs[tileHi][tileLo]):
                                if tileUniqueClrsPalClr[tileHi][tileLo][n] == mergeSumIndexA:
                                    if tileUniqueClrsPalDist[tileHi][tileLo][n] > splitDist:
                                        splitDist = tileUniqueClrsPalDist[tileHi][tileLo][n]
                                        splitIndex = n

                        tileMergePalR[j][mergeSumIndexB] = tileUniqueClrsR[tileHi][tileLo][splitIndex]
                        tileMergePalG[j][mergeSumIndexB] = tileUniqueClrsG[tileHi][tileLo][splitIndex]
                        tileMergePalR[j][mergeSumIndexB] = tileUniqueClrsB[tileHi][tileLo][splitIndex]
                        
    #done quantizing, copy the mergeBestPal back to the actual MergePal
    for n in range(15):
        tileMergePalR[j][n] = tileEMergeBestPalR[n]
        tileMergePalG[j][n] = tileEMergeBestPalG[n]
        tileMergePalB[j][n] = tileEMergeBestPalB[n]
        tileMergePalNumPix[j][n] = tileEMergeBestPalNumPix[n]
        tileMergePalNumClrs[j][n] = tileEMergeBestPalNumClrs[n]
    tileMergePalAvg[j] = bestAvgClrDistance
    

#=======================================================================================================================
#Dump final bitmap

print("Exporting Bitmap Reduced To {} Palettes...".format(fullPals))

with open(outputBMPNameC, "wb") as f:

    #Copy original header back verbatim
    for i in range(pixelStartAddress):
        f.write(bytelist[i])

    #Then write new pixel data
    for i in range(bitmapHeight):
        for j in range(bitmapWidth):
            tileCoordY = i%8
            tileCoordX = j%8
            mapCoordY = i//8
            mapCoordX = j//8

            #for each pixel, lookup which palette to use (FIND mapCoordY, mapCoordX IN tileMergePalTileList), find the closest colour match in that palette, then write that colour value
            
            foundTileMatch = False
            for n in range(fullPals):
                #print("PALETTE {}:  {} TILES".format(n, tileMergePalNumTiles[n]))
                for m in range(tileMergePalNumTiles[n]):
                    #print("{} == {}, {} == {}".format(tileMergePalTileList[n][m][0], mapCoordY, tileMergePalTileList[n][m][1], mapCoordX))
                    if tileMergePalTileList[n][m][0] == mapCoordY and tileMergePalTileList[n][m][1] == mapCoordX:
                        foundTileMatch = True
                        correctDrawPal = n
                        break
                if foundTileMatch == True:
                    break

            if foundTileMatch == False:
                print("WTF Tile not found {}, {}".format(mapCoordY, mapCoordX))
                quit()

            bestPixelDistance = 999999
            for n in range(15):
                pixelDistance = ((tileMergePalR[correctDrawPal][n] - tileClrsR[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)
                pixelDistance = pixelDistance + ((tileMergePalG[correctDrawPal][n] - tileClrsG[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)
                pixelDistance = pixelDistance + ((tileMergePalB[correctDrawPal][n] - tileClrsB[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)

                if pixelDistance < bestPixelDistance:
                    bestPixelDistance = pixelDistance
                    bestClrMatch = n

            tileDataOutputArray[bitmapHeight - i - 1][j] = bestClrMatch + 1        #Plus One Because Palette Colour Zero is Transparent!

            f.write(struct.pack("B", int(tileMergePalB[correctDrawPal][bestClrMatch] * 8)))
            f.write(struct.pack("B", int(tileMergePalG[correctDrawPal][bestClrMatch] * 8)))
            f.write(struct.pack("B", int(tileMergePalR[correctDrawPal][bestClrMatch] * 8)))

#=======================================================================================================================
#For when not dumping final bitmap, quickly and quietly populate tileDataOutputArray instead

#Write new pixel data
for i in range(bitmapHeight):
    for j in range(bitmapWidth):
        tileCoordY = i%8
        tileCoordX = j%8
        mapCoordY = i//8
        mapCoordX = j//8

        #for each pixel, lookup which palette to use (FIND mapCoordY, mapCoordX IN tileMergePalTileList), find the closest colour match in that palette, then write that colour value
        
        foundTileMatch = False
        for n in range(fullPals):
            for m in range(tileMergePalNumTiles[n]):
                if tileMergePalTileList[n][m][0] == mapCoordY and tileMergePalTileList[n][m][1] == mapCoordX:
                    foundTileMatch = True
                    correctDrawPal = n
                    break
            if foundTileMatch == True:
                break

        if foundTileMatch == False:
            print("WTF Tile not found {}, {}".format(mapCoordY, mapCoordX))
            quit()

        bestPixelDistance = 999999
        for n in range(15):
            pixelDistance = ((tileMergePalR[correctDrawPal][n] - tileClrsR[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)
            pixelDistance = pixelDistance + ((tileMergePalG[correctDrawPal][n] - tileClrsG[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)
            pixelDistance = pixelDistance + ((tileMergePalB[correctDrawPal][n] - tileClrsB[mapCoordY][mapCoordX][(tileCoordY*8)+tileCoordX]) ** 2)

            if pixelDistance < bestPixelDistance:
                bestPixelDistance = pixelDistance
                bestClrMatch = n

        tileDataOutputArray[bitmapHeight - i - 1][j] = bestClrMatch + 1        #Plus One Because Palette Colour Zero is Transparent!

#=======================================================================================================================
if binOut == True:
    #Output Tile Set - Consumes ONE FULL BANK for a fullscreen image
    print("Writing .bin file...")

    #Okay so DataOutputArray is always max size - 256x256.  Everything is zero beyond actual width and height.
    #write the FULL tileset EVERY time, INCLUDING all the blanks

    with open(outputBinNameA, "wb") as binf:
        #Note:  You can output as many rows as you want but j must ALWAYS be in range 32
        for i in range(RowsToOutput):
            for j in range(32):
                pixelClrNum = 0
                for k in range(8):
                    bitplane0[k] = ""
                    bitplane1[k] = ""
                    bitplane2[k] = ""
                    bitplane3[k] = ""
                for y in range(8):
                    for k in range(8):
                        pixelClrNum = tileDataOutputArray[(i * 8) + y][(j * 8) + k]
                        if pixelClrNum == 1 or pixelClrNum == 3 or pixelClrNum == 5 or pixelClrNum == 7 or pixelClrNum == 9 or pixelClrNum == 11 or pixelClrNum == 13 or pixelClrNum == 15:
                            bitplane0[y] = "{}1".format(bitplane0[y])
                        else:
                            bitplane0[y] = "{}0".format(bitplane0[y])
                        if pixelClrNum == 2 or pixelClrNum == 3 or pixelClrNum == 6 or pixelClrNum == 7 or pixelClrNum == 10 or pixelClrNum == 11 or pixelClrNum == 14 or pixelClrNum == 15:
                            bitplane1[y] = "{}1".format(bitplane1[y])
                        else:
                            bitplane1[y] = "{}0".format(bitplane1[y])
                        if pixelClrNum == 4 or pixelClrNum == 5 or pixelClrNum == 6 or pixelClrNum == 7 or pixelClrNum == 12 or pixelClrNum == 13 or pixelClrNum == 14 or pixelClrNum == 15:
                            bitplane2[y] = "{}1".format(bitplane2[y])
                        else:
                            bitplane2[y] = "{}0".format(bitplane2[y])
                        if pixelClrNum > 7:
                            bitplane3[y] = "{}1".format(bitplane3[y])
                        else:
                            bitplane3[y] = "{}0".format(bitplane3[y])

                #for y in range(8):
                #    bitplane0[y] = "%02X" % int(bitplane0[y], 2)
                #    bitplane1[y] = "%02X" % int(bitplane1[y], 2)
                #    bitplane2[y] = "%02X" % int(bitplane2[y], 2)
                #    bitplane3[y] = "%02X" % int(bitplane3[y], 2)
                
                binf.write(struct.pack("B", int(bitplane0[0], 2)))
                binf.write(struct.pack("B", int(bitplane1[0], 2)))
                binf.write(struct.pack("B", int(bitplane0[1], 2)))
                binf.write(struct.pack("B", int(bitplane1[1], 2)))
                binf.write(struct.pack("B", int(bitplane0[2], 2)))
                binf.write(struct.pack("B", int(bitplane1[2], 2)))
                binf.write(struct.pack("B", int(bitplane0[3], 2)))
                binf.write(struct.pack("B", int(bitplane1[3], 2)))
                binf.write(struct.pack("B", int(bitplane0[4], 2)))
                binf.write(struct.pack("B", int(bitplane1[4], 2)))
                binf.write(struct.pack("B", int(bitplane0[5], 2)))
                binf.write(struct.pack("B", int(bitplane1[5], 2)))
                binf.write(struct.pack("B", int(bitplane0[6], 2)))
                binf.write(struct.pack("B", int(bitplane1[6], 2)))
                binf.write(struct.pack("B", int(bitplane0[7], 2)))
                binf.write(struct.pack("B", int(bitplane1[7], 2)))

                binf.write(struct.pack("B", int(bitplane2[0], 2)))
                binf.write(struct.pack("B", int(bitplane3[0], 2)))
                binf.write(struct.pack("B", int(bitplane2[1], 2)))
                binf.write(struct.pack("B", int(bitplane3[1], 2)))
                binf.write(struct.pack("B", int(bitplane2[2], 2)))
                binf.write(struct.pack("B", int(bitplane3[2], 2)))
                binf.write(struct.pack("B", int(bitplane2[3], 2)))
                binf.write(struct.pack("B", int(bitplane3[3], 2)))
                binf.write(struct.pack("B", int(bitplane2[4], 2)))
                binf.write(struct.pack("B", int(bitplane3[4], 2)))
                binf.write(struct.pack("B", int(bitplane2[5], 2)))
                binf.write(struct.pack("B", int(bitplane3[5], 2)))
                binf.write(struct.pack("B", int(bitplane2[6], 2)))
                binf.write(struct.pack("B", int(bitplane3[6], 2)))
                binf.write(struct.pack("B", int(bitplane2[7], 2)))
                binf.write(struct.pack("B", int(bitplane3[7], 2)))      

        #=======================================================================================================================
        #Write Tilemap
        for i in range(numTilesTall):
            for j in range(numTilesWide):
                correctPaletteFound = False
                for k in range(fullPals):
                    for n in range(tileMergePalNumTiles[k]):
                        if tileMergePalTileList[k][n][0] == (numTilesTall - i - 1) and tileMergePalTileList[k][n][1] == j:
                            paletteRow = k
                            correctPaletteFound = True
                            break
                    if correctPaletteFound == True:
                        break
                if correctPaletteFound == False:
                    print("WTF Tile Not Found")
                    quit()
            
                if paletteRow == 0:
                    paletteStr = "000"
                if paletteRow == 1:
                    paletteStr = "001"
                if paletteRow == 2:
                    paletteStr = "010"
                if paletteRow == 3:
                    paletteStr = "011"
                if paletteRow == 4:
                    paletteStr = "100"
                if paletteRow == 5: 
                    paletteStr = "101"
                if paletteRow == 6:
                    paletteStr = "110"
                if paletteRow == 7:
                    paletteStr = "111"
                if paletteRow > 7:
                    print("Too Many Palettes to Export to SNES Properly!")
                
                #charStr needs to be a TEN bit binary string.  Top two bits represent what map chunk we're in.  Map is chunked from top to bottom in 4 parts.
                #Since it's 8x8 tiles, we'll be going with a LINEAR tileset arrangement - each full row of tiles is TWO full rows of tileset.

                charStr = format(int((i * 32) + j), '010b')

                binf.write(struct.pack("H", int("000{}{}".format(paletteStr, charStr), 2)))
                
            if numTilesWide < 32:
                for j in range(32 - numTilesWide):
                    binf.write(struct.pack("H", int("03FF", 16)))

        #Optional Map Padding
        #for i in range(32 - numTilesTall):
        #    for j in range(32):
        #        binf.write(struct.pack("H", int("03FF", 16)))

        #=======================================================================================================================        
        #Write Palettes
        for i in range(fullPals):
            binf.write(struct.pack("H", 0))
            for j in range(15):
                outputPalR = format(int(tileMergePalR[i][j]), '05b')
                outputPalG = format(int(tileMergePalG[i][j]), '05b')
                outputPalB = format(int(tileMergePalB[i][j]), '05b')

                binf.write(struct.pack("H", int("0{}{}{}".format(outputPalB, outputPalG, outputPalR), 2)))
                
        for i in range(targetNumPalettes - fullPals):
            print("Final # palettes is less than target!  Padding palette table up to target to maintain constant file size")
            for j in range(16):
                binf.write(struct.pack("H", 0))
            
    print ("Done")

#=======================================================================================================================        
#else:
    #Output Tile Set - Consumes ONE FULL BANK for a fullscreen image
#    print("Writing .inc files...")

    #Okay so DataOutputArray is always max size - 256x256.  Everything is zero beyond actual width and height.
    #write the FULL tileset EVERY time, INCLUDING all the blanks

#    with open(outputIncNameA, "w") as f:
#        f.write(outputIncNameALabel+'\r'+'\n')
        #Note:  You can output as many rows as you want but j must ALWAYS be in range 32
#        for i in range(RowsToOutput):
#            for j in range(32):
#                pixelClrNum = 0
#                for k in range(8):
#                    bitplane0[k] = ""
#                    bitplane1[k] = ""
#                    bitplane2[k] = ""
#                    bitplane3[k] = ""
#                for y in range(8):
#                    for k in range(8):
#                        pixelClrNum = tileDataOutputArray[(i * 8) + y][(j * 8) + k]
#                        if pixelClrNum == 1 or pixelClrNum == 3 or pixelClrNum == 5 or pixelClrNum == 7 or pixelClrNum == 9 or pixelClrNum == 11 or pixelClrNum == 13 or pixelClrNum == 15:
#                            bitplane0[y] = "{}1".format(bitplane0[y])
#                        else:
#                            bitplane0[y] = "{}0".format(bitplane0[y])
#                        if pixelClrNum == 2 or pixelClrNum == 3 or pixelClrNum == 6 or pixelClrNum == 7 or pixelClrNum == 10 or pixelClrNum == 11 or pixelClrNum == 14 or pixelClrNum == 15:
#                            bitplane1[y] = "{}1".format(bitplane1[y])
#                        else:
#                            bitplane1[y] = "{}0".format(bitplane1[y])
#                        if pixelClrNum == 4 or pixelClrNum == 5 or pixelClrNum == 6 or pixelClrNum == 7 or pixelClrNum == 12 or pixelClrNum == 13 or pixelClrNum == 14 or pixelClrNum == 15:
#                            bitplane2[y] = "{}1".format(bitplane2[y])
#                        else:
#                            bitplane2[y] = "{}0".format(bitplane2[y])
#                        if pixelClrNum > 7:
#                            bitplane3[y] = "{}1".format(bitplane3[y])
#                        else:
#                            bitplane3[y] = "{}0".format(bitplane3[y])

#                for y in range(8):
#                    bitplane0[y] = "%02X" % int(bitplane0[y], 2)
#                    bitplane1[y] = "%02X" % int(bitplane1[y], 2)
#                    bitplane2[y] = "%02X" % int(bitplane2[y], 2)
#                    bitplane3[y] = "%02X" % int(bitplane3[y], 2)

#                outputString = ".db $"
#                outputString = "{}{}, ${}, $".format(outputString, bitplane0[0], bitplane1[0])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane0[1], bitplane1[1])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane0[2], bitplane1[2])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane0[3], bitplane1[3])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane0[4], bitplane1[4])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane0[5], bitplane1[5])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane0[6], bitplane1[6])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane0[7], bitplane1[7])

#                outputString = "{}{}, ${}, $".format(outputString, bitplane2[0], bitplane3[0])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane2[1], bitplane3[1])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane2[2], bitplane3[2])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane2[3], bitplane3[3])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane2[4], bitplane3[4])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane2[5], bitplane3[5])
#                outputString = "{}{}, ${}, $".format(outputString, bitplane2[6], bitplane3[6])
#                outputString = "{}{}, ${}".format(outputString, bitplane2[7], bitplane3[7])

#                f.write(outputString+'\r'+'\n')

    #=======================================================================================================================
    #Write Tilemap
#    with open(outputIncNameB, "w") as f:
#        f.write(outputIncNameBLabel+'\r'+'\n')

#        for i in range(numTilesTall):
#            outputString = ".dw $"
#            for j in range(numTilesWide):
#                correctPaletteFound = False
#                for k in range(fullPals):
#                    for n in range(tileMergePalNumTiles[k]):
#                        if tileMergePalTileList[k][n][0] == (numTilesTall - i - 1) and tileMergePalTileList[k][n][1] == j:
#                            paletteRow = k
#                            correctPaletteFound = True
#                            break
#                    if correctPaletteFound == True:
#                        break
#                if correctPaletteFound == False:
#                    print("WTF Tile Not Found")
#                    quit()
            
#                if paletteRow == 0:
#                    paletteStr = "000"
#                if paletteRow == 1:
#                    paletteStr = "001"
#                if paletteRow == 2:
#                    paletteStr = "010"
#                if paletteRow == 3:
#                    paletteStr = "011"
#                if paletteRow == 4:
#                    paletteStr = "100"
#                if paletteRow == 5: 
#                    paletteStr = "101"
#                if paletteRow == 6:
#                    paletteStr = "110"
#                if paletteRow == 7:
#                    paletteStr = "111"
#                if paletteRow > 7:
#                    print("Too Many Palettes to Export to SNES Properly!")
                
                #charStr needs to be a TEN bit binary string.  Top two bits represent what map chunk we're in.  Map is chunked from top to bottom in 4 parts.
                #Since it's 8x8 tiles, we'll be going with a LINEAR tileset arrangement - each full row of tiles is TWO full rows of tileset.

#                charStr = format(int((i * 32) + j), '010b')

#                tileMapStr = "%04X" % int("000{}{}".format(paletteStr, charStr), 2)

#                if j == 31:
#                    outputString = "{}{}".format(outputString, tileMapStr)
#                else:
#                    outputString = "{}{}, $".format(outputString, tileMapStr)

#            if numTilesWide < 32:
#                for j in range(32 - numTilesWide - 1):
#                    outputString = "{}03FF, $".format(outputString)

#                outputString = "{}03FF".format(outputString)

#            f.write(outputString+'\r'+'\n')

        #Optional Map Padding
        #for i in range(32 - numTilesTall):
        #    outputString = ".dw $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF, $03FF"
        #    f.write(outputString+'\r'+'\n')

    #=======================================================================================================================        
    #Write Palettes
#    with open(outputIncNameC, "w") as f:
#        f.write(outputIncNameCLabel+'\r'+'\n')

#        for i in range(fullPals):
#            outputString = ".dw $0000, $"
#            for j in range(14):
#                outputPalR = format(int(tileMergePalR[i][j]), '05b')
#                outputPalG = format(int(tileMergePalG[i][j]), '05b')
#                outputPalB = format(int(tileMergePalB[i][j]), '05b')

#                outputPalAll = "%04X" % int("0{}{}{}".format(outputPalB, outputPalG, outputPalR), 2)
            
#                outputString = "{}{}, $".format(outputString, outputPalAll)

#            outputPalR = format(int(tileMergePalR[i][14]), '05b')
#            outputPalG = format(int(tileMergePalG[i][14]), '05b')
#            outputPalB = format(int(tileMergePalB[i][14]), '05b')

#            outputPalAll = "%04X" % int("0{}{}{}".format(outputPalB, outputPalG, outputPalR), 2)

#            outputString = "{}{}".format(outputString, outputPalAll)

#            f.write(outputString+'\r'+'\n')
    print ("Done")
