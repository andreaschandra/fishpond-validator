import os
import cv2
from datetime import timedelta
import pandas as pd
import numpy as np
import odc.stac
from pathlib import Path
import rioxarray
import planetary_computer as pc
from pystac_client import Client
import geopy.distance as distance

# get our bounding box to search latitude and longitude coordinates
def get_bounding_box(latitude, longitude, meter_buffer=50000):
    """
    Given a latitude, longitude, and buffer in meters, returns a bounding
    box around the point with the buffer on the left, right, top, and bottom.

    Returns a list of [minx, miny, maxx, maxy]
    """
    distance_search = distance.distance(meters=meter_buffer)

    # calculate the lat/long bounds based on ground distance
    # bearings are cardinal directions to move (south, west, north, and east)
    min_lat = distance_search.destination((latitude, longitude), bearing=180)[0]
    min_long = distance_search.destination((latitude, longitude), bearing=270)[1]
    max_lat = distance_search.destination((latitude, longitude), bearing=0)[0]
    max_long = distance_search.destination((latitude, longitude), bearing=90)[1]

    return [min_long, min_lat, max_long, max_lat]

# get our date range to search, and format correctly for query
def get_date_range(date, time_buffer_days=15):
    """Get a date range to search for in the planetary computer based
    on a sample's date. The time range will include the sample date
    and time_buffer_days days prior"""
    datetime_format = "%Y-%m-%dT"
    range_start = pd.to_datetime(date) - timedelta(days=time_buffer_days)
    date_range = f"{range_start.strftime(datetime_format)}/{pd.to_datetime(date).strftime(datetime_format)}"

    return date_range

def crop_sentinel_image(item, bounding_box):
    """
    Given a STAC item from Sentinel-2 and a bounding box tuple in the format
    (minx, miny, maxx, maxy), return a cropped portion of the item's visual
    imagery in the bounding box.
    """
    (minx, miny, maxx, maxy) = bounding_box

    image = rioxarray.open_rasterio(pc.sign(item.assets["visual"].href)).rio.clip_box(
        minx=minx,
        miny=miny,
        maxx=maxx,
        maxy=maxy,
        crs="EPSG:4326",
    )

    return image.to_numpy()

def crop_landsat_image(item, bounding_box):
    """
    Given a STAC item from Landsat and a bounding box tuple in the format
    (minx, miny, maxx, maxy), return a cropped portion of the item's visual
    imagery in the bounding box.
    """
    (minx, miny, maxx, maxy) = bounding_box

    image = odc.stac.stac_load(
        [pc.sign(item)], bands=["red", "green", "blue"], bbox=[minx, miny, maxx, maxy]
    ).isel(time=0)
    image_array = image[["red", "green", "blue"]].to_array().to_numpy()

    # normalize to 0 - 255 values
    image_array = cv2.normalize(image_array, None, 0, 255, cv2.NORM_MINMAX)

    return image_array

def select_best_item(items, date, latitude, longitude):
    """
    Select the best satellite item given a sample's date, latitude, and longitude.
    If any Sentinel-2 imagery is available, returns the closest sentinel-2 image by
    time. Otherwise, returns the closest Landsat imagery.

    Returns a tuple of (STAC item, item platform name, item date)
    """
    # get item details
    item_details = pd.DataFrame(
        [
            {
                "datetime": item.datetime.strftime("%Y-%m-%d"),
                "platform": item.properties["platform"],
                "min_long": item.bbox[0],
                "max_long": item.bbox[2],
                "min_lat": item.bbox[1],
                "max_lat": item.bbox[3],
                "item_obj": item,
            }
            for item in items
        ]
    )

    # filter to items that contain the point location, or return None if none contain the point
    item_details["contains_sample_point"] = (
        (item_details.min_lat < latitude)
        & (item_details.max_lat > latitude)
        & (item_details.min_long < longitude)
        & (item_details.max_long > longitude)
    )
    item_details = item_details[item_details["contains_sample_point"] == True]
    if len(item_details) == 0:
        return (np.nan, np.nan, np.nan)

    # add time difference between each item and the sample
    item_details["time_diff"] = pd.to_datetime(date) - pd.to_datetime(
        item_details["datetime"]
    )

    # if we have sentinel-2, filter to sentinel-2 images only
    item_details["sentinel"] = item_details.platform.str.lower().str.contains(
        "sentinel"
    )
    if item_details["sentinel"].any():
        item_details = item_details[item_details["sentinel"] == True]

    # return the closest imagery by time
    best_item = item_details.sort_values(by="time_diff", ascending=True).iloc[0]

    return (best_item["item_obj"], best_item["platform"], best_item["datetime"])

def main():
    DATA_DIR = "data"

    # save image arrays in case we want to generate more features
    IMAGE_ARRAY_DIR = os.path.join(DATA_DIR, "image_arrays")
    os.makedirs(IMAGE_ARRAY_DIR, exist_ok=True)
    print("image arrays dir created")

    farm_location = [
        (-7.675039,107.769191, 'jawa'),
        (-7.786883,108.155444, 'jawa'),
        (-5.552498,120.375194, 'sulawesi'),
        (-5.559804,120.376871, 'sulawesi'),
        (-5.573898,120.384974, 'sulawesi')
    ]

    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace
    )

    d_metadata = pd.DataFrame(farm_location, columns=['latitude', 'longitude', 'island'])

    # end of the summer in ID, which later to look up previous days
    d_metadata['date'] = '2022-08-31'
    d_metadata['uid'] = list(range(len(farm_location)))

    # save outputs in dictionaries
    for _, row in d_metadata.iterrows():
        image_array_pth = os.path.join(IMAGE_ARRAY_DIR, f"{row.island}_{row.latitude}_{row.longitude}_{row.uid}.jpg")
            
        search_bbox = get_bounding_box(
            row.latitude, row.longitude, meter_buffer=50000
        )
        date_range = get_date_range(row.date, time_buffer_days=30)
        
        #search the planetary computer
        search = catalog.search(
            collections=["sentinel-2-l2a", "landsat-c2-l2"],
            bbox=search_bbox,
            datetime=date_range
        )
        items = [item for item in search.get_all_items()]
        
        if len(items) == 0:
            pass
        else:
            best_item, item_platform, item_date = select_best_item(items, row.date, row.latitude, row.longitude)
            
        feature_bbox = get_bounding_box(row.latitude, row.longitude, meter_buffer=500)
        
        if "sentinel" in item_platform.lower():
            image_array = crop_sentinel_image(best_item, feature_bbox)
        else:
            image_array = crop_landsat_image(best_item, feature_bbox)
            
        # save image
        image_array = np.transpose(image_array, axes=[1, 2, 0])
        cv2.imwrite(image_array_pth, image_array)
        print("save image", image_array_pth)

if __name__ == "__main__":
    main()