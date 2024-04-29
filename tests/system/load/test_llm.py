# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pandas as pd
import pytest

import bigframes.ml.llm


@pytest.fixture(scope="session")
def llm_fine_tune_df_default_index(
    session: bigframes.Session,
) -> bigframes.dataframe.DataFrame:
    training_table_name = "llm_tuning.emotion_classification_train"
    df = session.read_gbq(training_table_name)
    prefix = "Please do sentiment analysis on the following text and only output a number from 0 to 5 where 0 means sadness, 1 means joy, 2 means love, 3 means anger, 4 means fear, and 5 means surprise. Text: "
    df["prompt"] = prefix + df["text"]
    df["label"] = df["label"].astype("string")
    return df


@pytest.fixture(scope="session")
def llm_remote_text_pandas_df():
    """Additional data matching the penguins dataset, with a new index"""
    return pd.DataFrame(
        {
            "prompt": [
                "Please do sentiment analysis on the following text and only output a number from 0 to 5where 0 means sadness, 1 means joy, 2 means love, 3 means anger, 4 means fear, and 5 means surprise. Text: i feel beautifully emotional knowing that these women of whom i knew just a handful were holding me and my baba on our journey",
                "Please do sentiment analysis on the following text and only output a number from 0 to 5 where 0 means sadness, 1 means joy, 2 means love, 3 means anger, 4 means fear, and 5 means surprise. Text: i was feeling a little vain when i did this one",
                "Please do sentiment analysis on the following text and only output a number from 0 to 5 where 0 means sadness, 1 means joy, 2 means love, 3 means anger, 4 means fear, and 5 means surprise. Text: a father of children killed in an accident",
            ],
        }
    )


@pytest.fixture(scope="session")
def llm_remote_text_df(session, llm_remote_text_pandas_df):
    return session.read_pandas(llm_remote_text_pandas_df)


def test_llm_palm_configure_fit(llm_fine_tune_df_default_index, llm_remote_text_df):
    model = bigframes.ml.llm.PaLM2TextGenerator(
        model_name="text-bison", max_iterations=1
    )

    df = llm_fine_tune_df_default_index.dropna()
    X_train = df[["prompt"]]
    y_train = df[["label"]]
    model.fit(X_train, y_train)

    assert model is not None

    df = model.predict(llm_remote_text_df["prompt"]).to_pandas()
    assert df.shape == (3, 4)
    assert "ml_generate_text_llm_result" in df.columns
    series = df["ml_generate_text_llm_result"]
    assert all(series.str.len() == 1)

    # TODO(ashleyxu b/335492787): After bqml rolled out version control: save, load, check parameters to ensure configuration was kept


def test_llm_palm_score(llm_fine_tune_df_default_index):
    model = bigframes.ml.llm.PaLM2TextGenerator(model_name="text-bison")

    # Check score to ensure the model was fitted
    score_result = model.score(
        X=llm_fine_tune_df_default_index[["prompt"]],
        y=llm_fine_tune_df_default_index[["label"]],
    ).to_pandas()
    score_result_col = score_result.columns.to_list()
    expected_col = [
        "bleu4_score",
        "rouge-l_precision",
        "rouge-l_recall",
        "rouge-l_f1_score",
        "evaluation_status",
    ]
    assert all(col in score_result_col for col in expected_col)


def test_llm_palm_score_params(llm_fine_tune_df_default_index):
    model = bigframes.ml.llm.PaLM2TextGenerator(
        model_name="text-bison", max_iterations=1
    )

    # Check score to ensure the model was fitted
    score_result = model.score(
        X=llm_fine_tune_df_default_index["prompt"],
        y=llm_fine_tune_df_default_index["label"],
        task_type="classification",
    ).to_pandas()
    score_result_col = score_result.columns.to_list()
    expected_col = [
        "trial_id",
        "precision",
        "recall",
        "accuracy",
        "f1_score",
        "log_loss",
        "roc_auc",
    ]
    assert all(col in score_result_col for col in expected_col)