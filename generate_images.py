import os
import pickle
import importlib.util
import subprocess
from collections import Counter
from PIL import Image, ImageDraw
from math import asin, acos, pi

# Generate new planet from scratch vs. use the existing .py or .pickle file
GENERATE_FROM_SCRATCH = True
# Path to racket executable
RACKET_PATH = r'C:\Program Files\Racket\racket.exe'
# Save dict to internal python binary format (faster reuse)
SAVE_PICKLE = True
# Planet size parameter (between 0 and 4)
# 0 produces no hexes and 12 pentagons; 5 results in MemoryError
PLANET_CHARACTERISTIC_SIZE = 3

# Directory with icons.
PICS = r'./pics/'
# Icons' extension
IMAGE_EXT = '.png'
# A portion of a tile (e.g. hex) occupied by an icon. An icon is assumed to have equal height and width
PIC_RATIO = 0.8

# Input directory
INPUT = r'./input/'
# Output directory
OUTPUT = r'./output/'
# .py file name
PY = f'earthgen_export_{PLANET_CHARACTERISTIC_SIZE}.py'
# .pickle file name
PICKLE = f'p{PLANET_CHARACTERISTIC_SIZE}.pickle'

# Save Dymaxion projection?
SAVE_DYMAXION = False
# Dymaxion projection file name (including extension)
DYMAXION = f'dymaxion_{PLANET_CHARACTERISTIC_SIZE}.png'
# The side length of a hexagon in pixels for dymaxion projections. Affects the resolution of the
# resulting image. If the resulting quality of the tiles is poor, make it <= HEX_R
DYMAXION_HEX_R = 50

# Save equirectangular projection?
SAVE_EQUIRECTANGULAR = True
# Save equirectangular projection heightmap?
SAVE_EQUIRECTANGULAR_HEIGHT = False
# Equirectangular projection file name (including extension) and the corresponding height map
EQUIRECTANGULAR = f'equirectangular_{PLANET_CHARACTERISTIC_SIZE}.png'
EQUIRECTANGULAR_HEIGHT = f'equirectangular_height_{PLANET_CHARACTERISTIC_SIZE}.png'
# The number of pixels for 1 degree of latitude and longitude. Affects the resolution of the
# resulting image.
EQUIRECTANGULAR_DEGREE = 20

# Grid Color (RGBA, ex. (0, 0, 0, 255)) or None (the color of the corresponding hex will be used)
GRID_COLOR = (0, 0, 0, 255)

# Settings for tile's  classification.
#   Elevation classifies the tile as a
#       Moutain (> MOUNTAIN_ELEVATION)
#       Hill (< MOUNTAIN_ELEVATION    and    > HILL_ELEVATION)
#       Flat Land (< HILL_ELEVATION    and    > 0)
#       Shallow Ocean (< 0    and    > MID_OCEAN)
#       Mid-Ocean (< MID_OCEAN    and    > DEEP_OCEAN)
#       Deep Ocean (< DEEP_OCEAN)
MOUNTAIN_ELEVATION = 1000
HILL_ELEVATION = 500
MID_OCEAN = - 1500
DEEP_OCEAN = - 3500

#   Uses Leaf-Area-Index to classify the tile as a Heavy Forest, Forest, Savanna, Tundra, Grass, or Desert
#   The conditions for Leaf-Area-Index must be met during at least one season.
#       Heavy Forest (> HEAVY_FOREST_LAI)
#       Forest (< HEAVY_FOREST_LAI    and    > FOREST_LAI)
#       Savanna (< FOREST_LAI    and    > SAVANNA_TUNDRA_LAI)   <---- must also satisfy that
#                                                                     minimal temperature > SAVANNA_MIN_TEMPERATURE
#                                                                     during all seasons. Otherwise considered Tundra
#       Tundra (< SAVANNA_TUNDRA_LAI    and    > LAND_LAI)      <----/
#       Grass (< SAVANNA_TUNDRA_LAI    and    > LAND_LAI)
#       Desert (< LAND_LAI)
HEAVY_FOREST_LAI = 8
FOREST_LAI = 6.5
SAVANNA_TUNDRA_LAI = 5.98
LAND_LAI = 4
SAVANNA_MIN_TEMPERATURE = 30 + 273.15

#   Desert might be sand, snowy, or neither (bare land). The desert is considered warm if
#   the temperature doesn't fall bellow SAND_DESERT_MIN_TEMPERATURE during any season.
#   The desert is snowy if max temperature durin all seasons is below SNOW_DESERT_MAX_TEMPERATURE
#   Otherwise, it's a bare land.
SAND_DESERT_MIN_TEMPERATURE = 10 + 273.15
SNOW_DESERT_MAX_TEMPERATURE = 10 + 273.15

#   Classifies a tile as a Wetland. Wetland must be on Flat Land and have precipitation greater
#   than WETLANDS_PRECIPITATION during all seasons except seasons when the tile is covered by snow,
#   i.e., frozen.
#
#   If the Leaf-Area-Index > SAVANNA_TUNDRA_LAI, then the tile is classified as a Swamp, otherwise it's a Marsh
WETLANDS_PRECIPITATION = 2e-8

#   Classifies the forest tile as one of the Jungle, Boreal, Mixed, Deciduous based on the variation of
#   Leaf-Area-Index across the seasons. The minimal
#       Jungle Forest (the absolute change in Leaf-Area-Index < JUNGLE_SEASONAL_LAI_VARIATION
#                      and temperature > JUNGLE_MIN_TEMPERATURE during all seasons)
#       Boreal Forest (the absolute change in Leaf-Area-Index < BOREAL_SEASONAL_LAI_VARIATION
#                      and temperature < JUNGLE_MIN_TEMPERATURE during at least one season)
#       Mixed Forest (the absolute change in Leaf-Area-Index < DECIDUOUS_SEASONAL_LAI_VARIATION
#                     and the absolute change in Leaf-Area-Index > BOREAL_SEASONAL_LAI_VARIATION)
#       Deciduous Forest (the absolute change in Leaf-Area-Index > DECIDUOUS_SEASONAL_LAI_VARIATION)

JUNGLE_SEASONAL_LAI_VARIATION = 2
BOREAL_SEASONAL_LAI_VARIATION = 6.5
DECIDUOUS_SEASONAL_LAI_VARIATION = 8
JUNGLE_MIN_TEMPERATURE = 30 + 273.15

# Classifies the tile as snowy if the fraction of seasons when tile is covered in snow is
# at least SEASONAL_SNOW_RATIO. Note: only some tiles can be snowy
SEASONAL_SNOW_RATIO = 0.75

# Background colors for the corresponding tiles (RGB)
COLORS = {
    'Jungle Forest': (94, 178, 106),
    'Heavy Jungle Forest': (94, 178, 106),
    'Deciduous Forest': (156, 204, 99),
    'Heavy Deciduous Forest': (156, 204, 99),
    'Mixed Forest': (122, 178, 69),
    'Heavy Mixed Forest': (122, 178, 69),
    'Boreal Forest': (79, 158, 69),
    'Heavy Boreal Forest': (79, 158, 69),
    'Snowy Boreal Forest': (229, 229, 229),
    'Heavy Snowy Boreal Forest': (229, 229, 229),
    'Grass': (160, 215, 107),
    'Sand Desert': (242, 227, 120),
    'Bare Land': (168, 159, 109),
    'Snow Desert': (229, 229, 229),
    'Savanna': (202, 227, 110),
    'Tundra': (160, 215, 107),
    'Swamp': (161, 214, 158),
    'Marsh': (173, 222, 166),
    'Hill Jungle Forest': (97, 135, 66),
    'Hill Deciduous Forest': (154, 180, 66),
    'Hill Mixed Forest': (132, 159, 45),
    'Hill Boreal Forest': (103, 139, 47),
    'Hill Snowy Boreal Forest': (229, 229, 229),
    'Hill Savanna': (217, 219, 112),
    'Hill Tundra': (160, 215, 107),
    'Mountain Jungle Forest': (199, 143, 0),
    'Mountains Jungle Forest': (178, 128, 0),
    'Mountain Deciduous Forest': (199, 143, 0),
    'Mountains Deciduous Forest': (178, 128, 0),
    'Mountain Mixed Forest': (199, 143, 0),
    'Mountains Mixed Forest': (178, 128, 0),
    'Mountain Boreal Forest': (199, 143, 0),
    'Mountains Boreal Forest': (178, 128, 0),
    'Mountain Snowy Boreal Forest': (199, 143, 0),
    'Mountains Snowy Boreal Forest': (178, 128, 0),
    'Mountain': (199, 143, 0),
    'Mountains': (178, 128, 0),
    'Snowy Mountain': (199, 143, 0),
    'Snowy Mountains': (178, 128, 0),
    'Surface Ocean': (29, 78, 145),
    'Mid Ocean': (18, 45, 95),
    'Deep Ocean': (8, 20, 49),
}

# add snowy tiles


# Changes the structure of imported planet variable
def merge_slices(planet):
    planet_size = int(((1 + 8 * len(planet[0][0]))**0.5 + 1) / 4)
    new_planet = []
    for season in planet:
        new_planet.append({})
        for i, sl in enumerate(season):
            for hx, params in sl.items():
                corrected_hx = hx[0] + (planet_size - 1) * i, hx[1]
                if corrected_hx not in new_planet[-1]:
                    new_planet[-1][corrected_hx] = params
    return new_planet, planet_size

# Classifies the tile
def type_of_hex(hx, planet):
    def seasonal(param):
        return [season[hx][param] for season in planet]
    def spread(lst):
        return max(lst) - min(lst)
    
    lai = seasonal('lai')
    precip = seasonal('precipitation')
    snow = seasonal('snow')
    temp = seasonal('temperature')
    elevation = planet[0][hx]['elevation']
    snowy_threshold = SEASONAL_SNOW_RATIO * len(planet)
    
    result = ''
    
    # Oceans
    if elevation < DEEP_OCEAN:
        return 'Deep Ocean'
    elif elevation < MID_OCEAN:
        return 'Mid Ocean'
    elif elevation < 0:
        return 'Surface Ocean'
    
    # Wetlands
    if (elevation < HILL_ELEVATION and 
      all([(pre > WETLANDS_PRECIPITATION or sn > 0) for (pre, sn) in zip(precip, snow)]) and
      sum(snow) < snowy_threshold):
        if max(lai) > SAVANNA_TUNDRA_LAI:
            return 'Swamp'
        else:
            return 'Marsh'
    
    # Forests
    if max(lai) > FOREST_LAI:
        if (spread(lai) < JUNGLE_SEASONAL_LAI_VARIATION
          and min(temp) > JUNGLE_MIN_TEMPERATURE
          and sum(snow) < snowy_threshold):
            result += 'Jungle Forest'
        elif (spread(lai) < BOREAL_SEASONAL_LAI_VARIATION or sum(snow) >= snowy_threshold):
            if sum(snow) < snowy_threshold:
                result += 'Boreal Forest'
            else:
                result += 'Snowy Boreal Forest'
        elif spread(lai) > DECIDUOUS_SEASONAL_LAI_VARIATION:
            result += 'Deciduous Forest'
        else:
            result += 'Mixed Forest'
        
        if elevation > MOUNTAIN_ELEVATION:
            result = ('Mountain ', 'Mountains ')[int(elevation % 2)] + result
        elif elevation > HILL_ELEVATION:
            result = 'Hill ' + result
        elif max(lai) > HEAVY_FOREST_LAI:
            result = 'Heavy ' + result
        
        return result
    
    # Moutains with no forests
    if elevation > MOUNTAIN_ELEVATION:
        result = ('Mountain', 'Mountains')[int(elevation % 2)]
        if sum(snow) >= snowy_threshold or max([t - elevation / 100 for t in temp]) < 0:
            result = 'Snowy ' + result
        
        return result
    
    # Hills and Flat Lands with some trees (but not forests)
    if max(lai) > SAVANNA_TUNDRA_LAI:
        if min(temp) > SAVANNA_MIN_TEMPERATURE:
            result = 'Savanna'
        else:
            result = 'Tundra'
        if elevation > HILL_ELEVATION:
            result = 'Hill ' + result
        
        return result
    
    # Hills and Flat Lands with no trees (grass or deserts)
    if sum(snow) >= snowy_threshold:
        return 'Snow Desert'
    elif max(lai) > LAND_LAI:
        return 'Grass'
    elif min(temp) > SAND_DESERT_MIN_TEMPERATURE:
        return 'Sand Desert'
    elif max(temp) < SNOW_DESERT_MAX_TEMPERATURE:
        return 'Snow Desert'
    else:
        return 'Bare Land'

# Classifies all tiles, used in statistics
def type_of_hexes(planet):
    season = planet[0]
    hex_types = {}
    for hx in season:
        hex_types[hx] = type_of_hex(hx, planet)
    return hex_types

# Gathers statics of tile types
def gather_statistics(hex_types):
    def key_include(dct, word):
        s = 0
        for key in dct.keys():
            if word in key:
                s += dct[key]
        return s     
        
    hexes = hex_types.values()
    count = Counter(hexes)
    
    total = sum(count.values())
    water = key_include(count, 'Ocean')
    land = total - water
    hill = key_include(count, 'Hill')
    mountain = key_include(count, 'Mountain')
    flat = land - hill - mountain
    
    jungle = key_include(count, 'Jungle')
    deciduous = key_include(count, 'Deciduous')
    boreal = key_include(count, 'Boreal')
    mixed = key_include(count, 'Mixed')
    forest = key_include(count, 'Forest')
    
    savanna = key_include(count, 'Savanna')
    tundra = key_include(count, 'Tundra')
    grass = key_include(count, 'Grass')
    sand_desert = key_include(count, 'Sand Desert')
    snow_desert = key_include(count, 'Snow Desert')
    bare_land = key_include(count, 'Bare Land')
    all_deserts = sand_desert + snow_desert + bare_land
    
    marsh = key_include(count, 'Marsh')
    swamp = key_include(count, 'Swamp')
    wetlands = marsh + swamp
    
    output = ("Ocean: {:.2f}%\nLand: {:.2f}%\n    Hill: {:.2f}%\n    Mountain: {:.2f}%\n    Flat: {:.2f}%\n" +
              "Forests: {:.2f}%\n    Jungle: {:.2f}%\n    Deciduous: {:.2f}%\n    Boreal: {:.2f}%\n    Mixed: {:.2f}%\n" +
              "Savanna: {:.2f}%\nTundra: {:.2f}%\nGrass: {:.2f}%\n" +
              "Desert: {:.2f}%\n    Warm Desert: {:.2f}%\n    Snow Desert: {:.2f}%\n    Bare land: {:.2f}%\n" +
              "Wetlands: {:.2f}%\n    Marsh: {:.2f}%\n    Swamp: {:.2f}%")

    prc = lambda n, m: 100 * (n / m) if m > 0 else 0
    params = [prc(water, total), prc(land, total), prc(hill, land), prc(mountain, land), prc(flat, land),
              prc(forest, land), prc(jungle, forest), prc(deciduous, forest), prc(boreal, forest), prc(mixed, forest),
              prc(savanna, land), prc(tundra, land), prc(grass, land),
              prc(all_deserts, land), prc(sand_desert, all_deserts), prc(snow_desert, all_deserts), prc(bare_land, all_deserts),
              prc(wetlands, land), prc(marsh, wetlands), prc(swamp, wetlands)]

    # params = [water / total, land / total, hill / land, mountain / land, flat / land,
    #           forest / land, jungle / forest, deciduous / forest, boreal / forest, mixed / forest,
    #           savanna / land, tundra / land, grass / land,
    #           all_deserts / land, sand_desert / all_deserts, snow_desert / all_deserts, bare_land / all_deserts,
    #           wetlands / land, marsh / wetlands, swamp / wetlands]
    return output.format(*params)

# Imports icons for tiles
def import_tile_icons():
    def hex_coord(r, w):
        return [(w, 0), (2 * w, r / 2), (2 * w, 3 * r / 2), (w, 2 * r), (0, 3 * r / 2), (0, r / 2)]

    icons = {}
    for terrain, color in COLORS.items():
        try:
            figure = Image.open(PICS + terrain.lower().replace(" ", "") + IMAGE_EXT).convert('RGBA')
            icons[terrain] = figure
        except:
            #print("Cannot open icon for " + terrain)
            pass

    return icons

# Generates and save Dymaxion map projections
def save_dymaxion(planet, planet_size, icons):
    # in px
    hex_r = DYMAXION_HEX_R
    hex_hw = round(hex_r * 3 ** 0.5 / 2)
    figure_r = PIC_RATIO * hex_r

    def hex_cartesian_center_to_cartesian_vertices(x, y, r, hw):
        return [(x - hw, y - r / 2), (x, y - r), (x + hw, y - r / 2),
                (x + hw, y + r / 2), (x, y + r), (x - hw, y + r / 2)]

    def hex_index_to_cartesian_center(a, b, r, hw, planet_size):
        x, y = 2 * hw * (a + b / 2), 3 * b / 2 * r
        return x + planet_size * hw, y + r

    # width and height
    picture_size = round((11 * planet_size - 9) * hex_hw), round((4.5 * planet_size - 2.5) * hex_r)

    dymaxion = Image.new('RGBA', picture_size, color=(0,0,0,0))
    for hx in planet[0]:
        a, b = hx
        x, y = hex_index_to_cartesian_center(a, b, hex_r, hex_hw, planet_size)
        coords = hex_cartesian_center_to_cartesian_vertices(x, y, hex_r, hex_hw)
        tpe = type_of_hex(hx, planet)
        fill = COLORS[tpe]
        outline = GRID_COLOR or fill
        
        ImageDraw.Draw(dymaxion).polygon(coords, outline=outline, fill=fill)
        
        if tpe in icons:
            icon = icons[tpe]
            icon = icons[type_of_hex(hx, planet)]
            icon = icon.resize((round(2 * figure_r), round(2 * figure_r)), resample=Image.LANCZOS)
            dymaxion.paste(icon, (round(x - figure_r), round(y - figure_r)), icon)

    dymaxion.save(OUTPUT + DYMAXION)

# Generates and saves Equirectangular map and height map projections
def save_equirectangular(planet, icons, save_height=True):
    degree = EQUIRECTANGULAR_DEGREE
    max_height = max([tile['elevation'] for tile in planet[0].values()])

    def insert_points(lst):
        new_lst = []
        for i in range(len(lst)):
            v1 = lst[i]
            v2 = lst[(i + 1) % len(lst)]
            v = [s + t for (s, t) in zip(v1, v2)]
            v_norm = sum(vx ** 2 for vx in v) ** 0.5
            v = [vx / v_norm for vx in v]
            new_lst.extend([v1, v])
        return new_lst

    def divide_line(lst, n):
        for i in range(n):
            lst = insert_points(lst)
        return lst
        
    def cart_to_spherical(lst):
        # lamb, phi = longitude, latitude
        lamb = lambda x, y: acos(x / (x ** 2 + y ** 2) ** 0.5) * (1 if y > 0 else -1)
        phi = asin
        
        new_lst = []
        for i, (x, y, z) in enumerate(lst):
            try:
                new_lst.append((lamb(x, y), phi(z)))
            except ZeroDivisionError:
                # pole
                last_lamb, last_phi = new_lst[-1]
                max_phi = pi / 2 * (1 if last_phi > 0 else -1)
                new_lst.extend([(last_lamb, max_phi), (- last_lamb, max_phi)])
        return new_lst

    def spherical_to_img(lst, scale=degree):
        return [((lamb + pi) * 180 / pi * scale, (- phi + pi / 2) * 180 / pi * scale)   for (lamb, phi) in lst]

    def draw_tile_with_spherical_coordinates(img, coords, outline, fill, terrain=None):
        coords = spherical_to_img(coords)
        ImageDraw.Draw(img).polygon(coords, outline=outline, fill=fill)
        if terrain in icons:
            xs, ys = zip(*coords)
            tile_w, tile_h = max(xs) - min(xs), max(ys) - min(ys)
            icon_w, icon_h = round(tile_w * PIC_RATIO), round(tile_h * PIC_RATIO)
            icon_pos_x, icon_pos_y = (round(min(xs) + tile_w * (1 - PIC_RATIO) / 2), 
                                      round(min(ys) + tile_h * (1 - PIC_RATIO) / 2))

            icon = icons[terrain]
            icon = icon.resize((icon_w, icon_h), resample=Image.LANCZOS)
            img.paste(icon, (icon_pos_x, icon_pos_y), icon)

    equirectangular = Image.new('RGBA', (360 * degree, 180 * degree), color=(0, 0, 0))
    equirectangular_height = Image.new('RGBA', (360 * degree, 180 * degree), color=(0, 0, 0))
    draw = ImageDraw.Draw(equirectangular)
    draw_height = ImageDraw.Draw(equirectangular_height)

    for hx in planet[0]:
        cart_coords = planet[0][hx]['coords']
        cart_coords = divide_line(cart_coords, 3)
        
        ys = [y for (x, y, z) in cart_coords]
        special_case = cart_coords[0][0] < 0 and not (all(y > 0 for y in ys) or all(y < 0 for y in ys))
        
        coords = cart_to_spherical(cart_coords)
        tpe = type_of_hex(hx, planet)
        fill = COLORS[tpe]
        outline = GRID_COLOR or fill

        color_height = round(planet[0][hx]['elevation'] / max_height * 255)
        fill_height = (color_height,) * 3

        if special_case:
            all_coords = [[c if c[0] < 0 else (c[0] - 2 * pi, c[1]) for c in coords],
                          [c if c[0] > 0 else (c[0] + 2 * pi, c[1]) for c in coords]]
        else:
            all_coords = [coords]
        
        for c in all_coords:
            draw_tile_with_spherical_coordinates(equirectangular, c, outline, fill, tpe)
            draw_tile_with_spherical_coordinates(equirectangular_height, c, fill_height, fill_height)

    equirectangular.save(OUTPUT + EQUIRECTANGULAR)
    if save_height:
        equirectangular_height.save(OUTPUT + EQUIRECTANGULAR_HEIGHT)

if __name__ == '__main__':
    PICKLE_FILE_PATH = os.path.join(INPUT, PICKLE)
    PY_FILE_PATH = os.path.join(INPUT, PY)

    if GENERATE_FROM_SCRATCH:
        print('Generating planet based on parameters from extract.rkt')
        subprocess.check_call([RACKET_PATH, "export.rkt",
                            str(2 * PLANET_CHARACTERISTIC_SIZE), PY_FILE_PATH])
        print('Done')

    print('Reading the map')
    try:
        # try to load pickle first
        planet = pickle.load(open(PICKLE_FILE_PATH, 'rb'))
    except:
        print('    failed to load from .pickle file. Trying to load from .py file')
        spec = importlib.util.spec_from_file_location(PY, PY_FILE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        planet = module.planet
    print('Done')

    if SAVE_PICKLE:
        print('Saving map to .pickle file')
        pickle.dump(planet, open(PICKLE_FILE_PATH, "wb"))
        print('Done')

    print('Classifying tiles')
    planet, planet_size = merge_slices(planet)
    converted_tiles = type_of_hexes(planet)
    print('Done')

    print('\n' + '=' * 25 + '\nYou planet statistics:\n')
    print(gather_statistics(converted_tiles))
    print('=' * 25)

    icons = import_tile_icons()

    if SAVE_DYMAXION:
        print(f'Saving Dymaxion projection to {OUTPUT}{DYMAXION}')
        save_dymaxion(planet, planet_size, icons)
        print('Done')

    if SAVE_EQUIRECTANGULAR:
        message = ('Saving Equirectangular projection ' + ('and Heigtmap ' if SAVE_EQUIRECTANGULAR_HEIGHT else '') +
                   f'to {OUTPUT}{EQUIRECTANGULAR}' +
                   (f'and {OUTPUT}{EQUIRECTANGULAR_HEIGHT}' if SAVE_EQUIRECTANGULAR_HEIGHT else '')) 
        print(message)
        save_equirectangular(planet, icons, save_height=SAVE_EQUIRECTANGULAR_HEIGHT)
        print('Done')

    print('Finished')
