# Test with another land-use source: MapBiomas (grid only, not part of the main result)

Manuscript, section 5.4.3. The main runs use the land-cover layer of the LuccME-BR database (NetCDF, pixels of about
100 km²). At 5.28 km the land-use bands therefore carry no information finer than that source. This test builds the
5.28 km cell space with MapBiomas (collection 11, 30 m, CC-BY-4.0, year 2000, the year of the main layer) instead,
to exercise the ingestion of another open source at national scale and to measure its cost. **It generates the
grid only. The model is not run on it and no result of section 5.4 depends on it.**

## Why it needs a script

DisSCube 0.5.0 reads the whole window of a `mapbiomas` source into memory as float32. Over Brazil at 30 m that is
about 9.4 billion pixels (more than 35 GB), so a single `disscube run` over the national grid does not fit. The
script runs DisSCube one BDC_SM tile (105.6 km) at a time, only on tiles that hold cells of the mask (865 of the
2,340 tiles of the bounding box at 5.28 km), and records time and peak memory per tile.

## Steps

```bash
pip install -r requirements.txt            # disscube 0.5.0
# 1. try a few tiles first, to time them (tile indices: column,row, both counted from the top-left of the grid)
python scripts/build_mapbiomas_cellspace.py --base data/raw_cellspace_bdc_5k.tif \
    --out data/raw_cellspace_bdc_5k_mapbiomas_try.tif --workdir data/mapbiomas_try --tiles "25,10;26,10"
# 2. all tiles (--jobs runs tiles at the same time; --resume keeps the tiles already finished)
python scripts/build_mapbiomas_cellspace.py --base data/raw_cellspace_bdc_5k.tif \
    --out data/raw_cellspace_bdc_5k_mapbiomas.tif --workdir data/mapbiomas_5k --jobs 3 --resume
# 3. same completion step as the main cell space, then the checks
python scripts/complete_cellspace.py data/raw_cellspace_bdc_5k_mapbiomas.tif data/cellspace_bdc_5k_mapbiomas.tif
python scripts/check_cellspace.py data/cellspace_bdc_5k_mapbiomas.tif
```

`data/mapbiomas_5k/build_report.json` has the wall time, the peak memory, the time of every tile, the number of
cells of the mask without MapBiomas data, and the area of each class in the NetCDF layer and in MapBiomas (a
consistency check between two sources for the same year).

## Choices that are ours

- The correspondence between MapBiomas codes and the seven classes is declared in
  `model/mapbiomas_crosswalk.toml`. It is not the one of LuccME-BR, and the legend of collection 11 must be
  checked ([TO CONFIRM] in the file).
- Codes that are not listed go to `others`; code 0 (not observed) is nodata, and a cell with no observed pixel
  is left empty and removed by `complete_cellspace.py`, as in the main cell space.
- The drivers and the mask are those of the base cell space.

## Pilot on the published files (author's machine, 10 Oct 2026)

Two tiles in Pará (25,10 and 26,10; 400 cells of the mask each): 29.1 s and 31.8 s per tile, peak memory 521 MB
(process tree), windows of 3551 x 3553 pixels, no pixel without data, shares summing to 1 in all 800 cells. The
process used about 54% of one CPU, so the time is dominated by the network. Sequentially, 865 tiles at this rate
would take about 7 hours; `--jobs` runs tiles at the same time.

## What was tested here

On a synthetic MapBiomas raster (EPSG:4326, 0.02°) and the real 5.28 km base cell space, two tiles: the seven
shares sum to 1 in every cell, the drivers are unchanged, and the per-tile report is written. Reading the published files, the time and the memory were tested by the author (pilot above). Not yet done:
the whole country, and the comparison of class areas with the NetCDF layer.
