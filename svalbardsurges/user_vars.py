label = 'svalbard'
products = ['ATL06']
date_range = ['2019-09-01', '2019-10-31']

rgi_path = 'data/rgi.gpkg'

spatial_extents = {
    'heerland': [16.65, 77.65, 18.4, 78],
    'heerlandextended': [14, 76, 19, 78],
    'svalbard': [5, 70, 40, 89],
    'south': [5, 70, 19, 78]
}
spatial_extent = spatial_extents[label]

dy = True


