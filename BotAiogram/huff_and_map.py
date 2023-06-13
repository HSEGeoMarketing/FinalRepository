import webbrowser

import folium
import osmnx as ox

# for distance
from math import sin, cos, sqrt, atan2, radians
# for Polygon square
from shapely.geometry import mapping


class Store:
    def __init__(self, square, lat, lon):
        self.square = square
        self.lat = lat
        self.lon = lon


class Residental:
    def __init__(self, population, lat, lon):
        self.population = population
        self.lat = lat
        self.lon = lon


# distance between two dots in km
def calculate_distance(lat1, lon1, lat2, lon2):
    earth_radius = 6373.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = earth_radius * c
    return distance


def is_nan(val):
    return val != val


# getting shop parameters to calculate Huff
def fill_shops(shops):
    shops_huff = []



    for shop_point, shop_name in zip(shops['geometry'], shops['name']):

        if shop_point.geom_type == 'Point':
            shop_lon = shop_point.x
            shop_lat = shop_point.y

            if shop_name == 'Магнит':
                shop_square = 400
            elif shop_name == 'Перекресток':
                shop_square = 1000
            elif shop_name == 'Дикси':
                shop_square = 350
            elif shop_name == 'Пятерочка':
                shop_square = 400
            elif shop_name == 'Карусель':
                shop_square = 4000
            elif shop_name == 'Семишагофф':
                shop_square = 250
            elif shop_name == 'ВкусВилл':
                shop_square = 150
            elif shop_name == 'Лента':
                shop_square = 2200
            elif shop_name == 'Ашан':
                shop_square = 11500
            elif shop_name == 'Окей':
                shop_square = 7300
            elif shop_name == 'Метро Кэш энд Керри' or shop_name == 'Metro' or shop_name == 'Метро':
                shop_square = 6000
            else:
                shop_square = 75

        else:
            shop_lon = shop_point.centroid.x
            shop_lat = shop_point.centroid.y

            shop_square = shop_point.area * (40000000 / 360) ** 2 / 2

        shops_huff.append(Store(square=shop_square, lat=shop_lat, lon=shop_lon))

    return shops_huff


# getting residental parameters to calculate Huff
def fill_apartments(apartments):
    apart_huff = []

    for building_type, apart_point, apart_levels in zip(apartments['building'], apartments['geometry'],
                                                        apartments['building:levels']):

        if is_nan(apart_levels):
            apart_levels = 1

        apart_levels = float(apart_levels)

        if apart_point.geom_type == 'Point':
            apart_lon = apart_point.x
            apart_lat = apart_point.y

            if building_type == 'apartments':
                apart_population = apart_levels * 3 * 8
            else:
                apart_population = apart_levels * 3

        else:
            apart_lon = apart_point.centroid.x
            apart_lat = apart_point.centroid.y
            apart_square = apart_point.area * (40000000 / 360) ** 2 / 2

            if apart_levels >= 14:  #
                apart_levels -= 3

            apart_population = apart_square * 0.7 * apart_levels / 25

        apart_huff.append(Residental(population=apart_population, lat=apart_lat, lon=apart_lon))

    return apart_huff


def calculate_huff(current_shop_lat, current_shop_lon, current_shop_square, radius_shop=2000,
                   radius_residental=1000):
    tags_apart = {'building': ['apartments', 'house']}
    tags_shop = {'shop': ['convenience', 'supermarket']}
    apartments = ox.geometries_from_point(tuple([current_shop_lat, current_shop_lon]), tags=tags_apart,
                                          dist=radius_residental)
    shops = ox.geometries_from_point(tuple([current_shop_lat, current_shop_lon]), tags=tags_shop, dist=radius_shop)

    apart_huff = fill_apartments(apartments)

    shops_huff = fill_shops(shops)
    # last element in "shops_huff" is the store to get Huff
    shops_huff.append(Store(square=current_shop_square, lat=current_shop_lat, lon=current_shop_lon))

    distance = []
    for i in range(len(apart_huff)):
        distance.append([])
        for j in range(len(shops_huff)):
            dist_ij = calculate_distance(apart_huff[i].lat, apart_huff[i].lon, shops_huff[j].lat, shops_huff[j].lon)
            distance[i].append(dist_ij)

    # Huff gravity model
    # P_ij = (S_j/ (T_ij**lmbd)) / (sum_k S_k/ (T_ik**lmbd))
    # P-probability, S-square, T-time(distance
    # i - number of quart, j- number of market
    lmbd = 0.0000001
    propabilities = []

    for i in range(len(apart_huff)):
        sum_k = 0
        for k in range(len(shops_huff)):
            sum_k += shops_huff[k].square / distance[i][k] ** lmbd
        propabilities.append([])
        for j in range(len(shops_huff)):
            propabilities[i].append((shops_huff[j].square / distance[i][j] ** lmbd) / sum_k)

    # potential customers from residental = probability * population
    huff_pred = sum(propabilities[i][-1] * apart_huff[i].population for i in range(len(apart_huff)))
    return huff_pred


def show_nearest_shops(current_shop_lat, current_shop_lon, shop_map, shops, radius_map=200):
    if 'name' in shops.keys():
        for shop_point, shop_name in zip(shops['geometry'], shops['name']):
            if is_nan(shop_name):
                shop_name = 'Магазин'  # check isNan

            if shop_point.geom_type == 'Point':
                shop_lon = shop_point.x  # lon == x
                shop_lat = shop_point.y  # lat == y

            else:  # geom_type == 'Polygon'
                shop_lon = shop_point.centroid.x
                shop_lat = shop_point.centroid.y

            if calculate_distance(current_shop_lat, current_shop_lon, shop_lat, shop_lon) * 1000 < radius_map:
                folium.Marker([shop_lat, shop_lon], tooltip=shop_name,
                              icon=folium.Icon(icon="glyphicon glyphicon-shopping-cart", color="red")).add_to(shop_map)


def show_nearest_apartments(current_shop_lat, current_shop_lon, shop_map, apartments, radius_map=200):
    for apartments_point in apartments['geometry']:
        apartments_lon = apartments_point.centroid.x  # lon == x
        apartments_lat = apartments_point.centroid.y  # lat == y
        if calculate_distance(current_shop_lat, current_shop_lon, apartments_lat,
                              apartments_lon) * 1000 < radius_map:
            folium.Marker([apartments_lat, apartments_lon],
                          icon=folium.Icon(icon="glyphicon glyphicon-home",
                                           color="blue")).add_to(shop_map)

        if apartments_point.geom_type == 'Polygon':

            apartments_lon = apartments_point.centroid.x
            apartments_lat = apartments_point.centroid.y

            if calculate_distance(current_shop_lat, current_shop_lon, apartments_lat,
                                  apartments_lon) * 1000 < radius_map:
                poly_line = list(mapping(apartments_point)['coordinates'][0])
                for i in range(0, len(poly_line)):
                    poly_line[i] = tuple(poly_line[i][::-1])
                folium.Polygon(poly_line, weight=5, color="blue", fill_color="blue", fill_opacity=0.3).add_to(shop_map)


def show_nearest_interest_points(current_shop_lat, current_shop_lon, radius_map=200, zoom=17):
    tags_apart = {'building': ['apartments', 'house']}
    tags_shop = {'shop': ['convenience', 'supermarket']}
    apart = ox.geometries_from_point(tuple([current_shop_lat, current_shop_lon]), tags=tags_apart,
                                     dist=radius_map)
    shops = ox.geometries_from_point(tuple([current_shop_lat, current_shop_lon]), tags=tags_shop, dist=radius_map)

    shop_map = folium.Map(location=[current_shop_lat, current_shop_lon], zoom_start=zoom, tiles='openstreetmap')
    folium.Circle(radius=radius_map * 1.1, location=tuple([current_shop_lat, current_shop_lon]), color="gray",
                  fill_opacity=0.15,
                  fill=True).add_to(shop_map)
    folium.Marker([current_shop_lat, current_shop_lon], tooltip="YOUR SHOP",
                  icon=folium.Icon(icon="glyphicon glyphicon-flag", color="green")).add_to(shop_map)

    show_nearest_shops(current_shop_lat, current_shop_lon, shop_map, shops, radius_map)
    show_nearest_apartments(current_shop_lat, current_shop_lon, shop_map, apart, radius_map)

    return shop_map


if __name__ == '__main__':
    current_shop_lat1 = 59.941889
    current_shop_lon1 = 30.230887
    current_shop_square1 = 100

    your_map = show_nearest_interest_points(current_shop_lat1, current_shop_lon1, radius_map=400, zoom=16)
    map_file = 'map.html'

    your_map.save(map_file)
    webbrowser.open(map_file, new=2)

    print(calculate_huff(current_shop_lat1, current_shop_lon1, current_shop_square1))
