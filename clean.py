import numpy as np
import pandas as pd
import logging
import os
from sklearn import preprocessing
from sklearn.impute import KNNImputer
from scipy import stats

pd.options.mode.chained_assignment = None  # default='warn'
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows", 300)
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger("clean")


def correct_lon_lat(df, ref_df):
    log.info("Correcting longitude latitude info")
    df["lon"] = ref_df["lon"]
    df["lat"] = ref_df["lat"]
    return df


def truncate_extreme_values(df):
    # Truncate extreme values above [1] percentile and below [2] percentile in [0] col
    cols = [("price_doc", 99.5, 0.5), ("full_sq", 99.5, 0.5), ("life_sq", 95, 5)]
    for col in cols:
        if col in df.columns:
            col_values = df[col[0]].to_numpy()
            upper_limit = np.percentile(
                np.delete(col_values, np.where(col_values == -99)), col[1]
            )
            lower_limit = np.percentile(
                np.delete(col_values, np.where(col_values == -99)), col[2]
            )
            df[col[0]].loc[df[col[0]] > upper_limit] = upper_limit
            df[col[0]].loc[df[col[0]] < lower_limit] = lower_limit
            log.info(
                "Truncating extreme values for col {}, {} percentile = {}, {} percentile = {}".format(
                    col[0], col[1], upper_limit, col[2], lower_limit
                )
            )
    return df


def convert_categorical_to_numerical(df):
    log.info("Converting categorical data to numerical")
    lb_encoder = preprocessing.LabelEncoder()
    for f in df.columns:
        if df[f].dtype == "object" and f != "timestamp":
            lb_encoder.fit(
                list(df[f].values.astype("str")) + list(df[f].values.astype("str"))
            )
            df[f] = lb_encoder.transform(list(df[f].values.astype("str")))
    return df


def impute_missing_values_data(df):
    log.info("Filling missing values using KNNimputer")
    # Fill NAN using sklearn's KNN imputer
    df_cp = df.copy()
    df = df.drop("timestamp", axis=1)
    imputer = KNNImputer(n_neighbors=5)
    df = pd.DataFrame(imputer.fit_transform(df), columns=df.columns)
    df["timestamp"] = df_cp["timestamp"].values
    return df


def impute_missing_values_macro(df):
    log.info("Filling missing values using KNNimputer")
    # Fill NAN using sklearn's KNN imputer
    df_cp = df.copy()
    imputer = KNNImputer(n_neighbors=5)
    df = pd.DataFrame(imputer.fit_transform(df), columns=df.columns)
    df.index = df_cp.index
    return df


def handle_bad_data(df):
    log.info("Handling bad data")
    # Remove records where kitchen squares and life squres are larger than full squares
    df = df.drop(df[df["life_sq"] > df["full_sq"]].index)
    df = df.drop(df[df["kitch_sq"] > df["full_sq"]].index)

    # Remove an outlier record with full_sq == 5326
    df = df.drop(df[df["full_sq"] == 5326].index)

    # Remove records where build year is less than 1691 and greater than 2018. Some entries include 0, 1, 3, 20, 71
    df = df.drop(df[df["build_year"] <= 1691].index)
    df = df.drop(df[df["build_year"] > 2018].index)

    # Remove records with max floor > 57 (99, 117)
    df = df.drop(df[df["max_floor"] > 57].index)

    # Remove records where actual floor > max floor
    df = df.drop(df[df["floor"] > df["max_floor"]].index)

    # Remove records where full_sq are 0 and 1 which are obvious errors
    df = df.drop(df[df["full_sq"] == 0].index)
    df = df.drop(df[df["full_sq"] == 1].index)

    # Remove records where max_floor is 0
    df = df.drop(df[df["max_floor"] == 0].index)

    # Remove records with erroneous school-related data
    df = df.drop(df[df["children_preschool"] < 0].index)
    df = df.drop(df[df["preschool_quota"] < 0].index)
    df = df.drop(df[df["children_school"] < 0].index)
    df = df.drop(df[df["school_quota"] < 0].index)

    # State should be discrete valued between 1 and 4. There is a 33 in it that is clearly a data entry error.
    # Replace it with mode of state
    df["state"].loc[df["state"] == 33] = stats.mode(df["state"].values)[0][0]

    # build_year has an erroneous value 20052009. Since its unclear which it should be.
    # Replace with 2007
    df["build_year"].loc[df["build_year"] == 20052009] = 2007

    return df


def clean_data(df, ref_df):
    log.info("Cleaning pipeline started")
    df = correct_lon_lat(df, ref_df)
    df = truncate_extreme_values(df)
    df = convert_categorical_to_numerical(df)
    df = impute_missing_values_data(df)
    df = handle_bad_data(df)
    return df


def clean_macro(df):
    log.info("Cleaning pipeline started")
    df = truncate_extreme_value(df)
    df = convert_categorical_to_numerical(df)
    df = impute_missing_values_macro(df)
    return df


# Environment Variables
TRAIN_PATH = "input/train.csv"
TEST_PATH = "input/test.csv"
MACRO_PATH = "input/macro.csv"
TRAIN_LAT_LON_PATH = "input/train_lat_lon.csv"
TEST_LAT_LON_PATH = "input/test_lat_lon.csv"
TRAIN_OUT_PATH = "output/train.csv"
TEST_OUT_PATH = "output/test.csv"
MACRO_OUT_PATH = "output/test.csv"
JOIN_TRAIN_MACRO_PATH = "output/train_macro.csv"
JOIN_TEST_MACRO_PATH = "output/test_macro.csv"

df_train = pd.read_csv(TRAIN_PATH, index_col="id")
df_test = pd.read_csv(TEST_PATH, index_col="id")
df_train_lat_lon = pd.read_csv(
    TRAIN_LAT_LON_PATH, usecols=["id", "lat", "lon"], index_col="id"
).sort_index()
df_test_lat_lon = pd.read_csv(
    TEST_LAT_LON_PATH, usecols=["id", "lat", "lon"], index_col="id"
).sort_index()
df_macro = pd.read_csv(MACRO_PATH, index_col="timestamp")

# Clean
df_train_clean = clean_data(df_train, df_train_lat_lon)
df_test_clean = clean_data(df_test, df_test_lat_lon)
df_macro_clean = clean_macro(df_macro)
df_train_clean.to_csv(TRAIN_OUT_PATH, index=False)
df_test_clean.to_csv(TEST_OUT_PATH, index=False)
df_macro_clean.to_csv(MACRO_OUT_PATH, index=False)

# Join
df_train_clean.merge(
    df_macro_clean, how="left", left_on="timestamp", right_index=True
).to_csv(JOIN_TRAIN_MACRO_PATH, index=False)
df_test_clean.merge(
    df_macro_clean, how="left", left_on="timestamp", right_index=True
).to_csv(JOIN_TEST_MACRO_PATH, index=False)
