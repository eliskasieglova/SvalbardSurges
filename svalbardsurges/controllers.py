# script for turning on and off certain parts of the code
validate = False  # validate data?
testdata = False  # run on test data?
pltshow = False  # show plots?
pltsave = False  # save plots?

rerun = False # rerun the downloads and analysis


# which data to use
gao_url = 'https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v7/regional_files/' \
                      'RGI2000-v7.0-G/RGI2000-v7.0-G-07_svalbard_jan_mayen.zip'
gao_ids = [
            # 12412,      # Storbreen
            13406.1,  # Scheelebreen
            13218.1,  # Doktorbreen
            # 17310.1,    # Hinlopenbreen
            # 15511.1     # Kongsbreen
        ]

test_ids = [
    "G018031E77579N",  # Kvalbreen
    'G016964E77694N',  # Scheelebreen
    'G017525E77773N',
    'G017911E77804N',
    'G016885E77574N',
    'G016172E77192N',  # Storbreen
    'G018042E78675N',  # Negribreen
    'G017497E78572N',  # Tunabreen
    'G023559E79453N',
    'G016807E77171N',
    'G015026E77342N',
    'G013095E79037N',
    'G025297E79771N',
    'G016482E76791N'
]
