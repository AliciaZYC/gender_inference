# 🧠 Multi-Signal Gender Inference AI Agent

## Version 2 🎬 [Demo Video Link](https://drive.google.com/file/d/1QrdpjsB79MIfbTwClW-svHe4I-FvCOxt/view?usp=sharing)

Version 2 main change is implementing MongoDB Atlas as the persistence layer with GridFS for binary storage. Profile images are no longer stored as filesystem paths but are instead managed through MongoDB's GridFS, enabling centralized binary storage that works seamlessly across distributed deployments—images are uploaded once to GridFS, downloaded as temporary files when needed for Face++ API calls, and automatically cleaned up after processing.

## 📜 Overview

This project implements a sophisticated, logic-driven AI Agent designed to accurately **infer (predict) a user's gender** when explicit information is missing. The Agent's core strength lies in its ability to **intelligently integrate and dynamically weigh** signals from three distinct sources: **name recognition, sports affiliation, and profile picture analysis**. This approach ensures high confidence scores and provides full attribution for every inference.

## ✨ Core Features

- **Multi-Source Fusion:** Integrates data from name guesser (gender-guesser), sports statistics, and external image recognition (Face++) APIs.
- **Dynamic Weighting:** Weights are conditionally assigned based on the **quality of each signal** (e.g., ambiguous names, mixed-gender sports, or low-quality/group photos).
- **Persistent Overrides:** Supports manual overrides or explicitly provided gender, which are **persisted** (via Dependency Injection) and strictly prevent future re-inference unless manually cleared.
- **Strict Opt-Out:** Inference is immediately bypassed if a persistent override or explicit gender input is detected.
- **Attribution & Review:** Outputs a structured result including a **confidence score** and **Signal Attribution**, flagging low-confidence cases for manual review.

---

## 💻 Core Logic Breakdown: Signal Fusion and Weighting

The `GenderInferenceAgent` executes its logic within the `infer_gender` pipeline, prioritizing signal quality and conflict resolution.

### 1\. Name Signal (`get_name_signal`)

This method determines the gender propensity and reliability based on the user's first name, utilizing an established open-source library.

| Element         | Tool / Data Source                                  | Logic Description                                                                                                                                                                                                        |
| :-------------- | :-------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tool**        | **`gender-guesser.detector`**                       | Used to classify the name's gender category (e.g., `'male'`, `'mostly_female'`, `'andy'`).                                                                                                                               |
| **Core Output** | **Signal Quality** ("high", "ambiguous", "unknown") | Maps the library's classification into quantifiable weights. Names classified as **"ambiguous"** (like "Alex" or "Andy") are given **extremely low confidence** ($0.1$) to minimize their influence on the final result. |

### 2\. Sport Signal (`get_sport_signal`)

This signal establishes a probabilistic baseline based on the athlete's team or sport affiliation.

| Element             | Data Source                                      | Logic Description                                                                                                                                                                                                       |
| :------------------ | :----------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Raw Data Source** | `sport_gender_data/tidytuesday_sports.csv`       | **(Original Source File)** Used by a separate process to calculate gender ratios for each sport.                                                                                                                        |
| **Agent Input**     | `sport_gender_data/sport_gender_ratios.json`     | The Agent consumes this pre-processed file, which stores the calculated **male ratio** for each sport.                                                                                                                  |
| **Core Output**     | **Signal Quality** ("explicit", "high", "mixed") | Identifies **explicit gender markers** ("Men's", "Women's") for near-absolute certainty. Sports with a mixed or balanced ratio (like "Track and Field") are marked **"mixed"** and assigned a low weight (e.g., $0.2$). |

### 3\. Dynamic Weighting and Image Integration

The Agent's intelligence is best demonstrated when resolving conflicting or ambiguous signals:

| Scenario                   | Decision Logic                                                                                                                    | Weight Adjustment                                                                                                                                               | Example (e.g., `athlete_003`)                                                                 |
| :------------------------- | :-------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------- |
| **Low Initial Confidence** | If confidence $< 70\%$ OR if signals are **"ambiguous" / "mixed"**.                                                               | Triggers `get_image_signal` to seek a third-party tie-breaker.                                                                                                  | Alex Wilson (**ambiguous name**) + Track and Field (**mixed sport**) triggers image analysis. |
| **Image Quality**          | Single, clear face gets the **highest weight** (e.g., $0.6$). Group photos with mixed gender get the lowest weight (e.g., $0.1$). | A high-quality image can **override a conflicting strong signal** (e.g., Female image on a "Men's Team" leads to a low final confidence and **manual review**). |
| **High Confidence**        | If initial Name + Sport confidence $\geq 70\%$.                                                                                   | **Image analysis is skipped** to save API resources and latency (e.g., `athlete_001`).                                                                          |

---

## 🛠️ Setup and Dependencies

### `requirements.txt`

```text
pandas
numpy
requests
gender-guesser
```

### Dependency Injection

The Agent requires an implementation of the `OverrideStore` interface to handle persistence. This is crucial for satisfying the **Overrides Persist** requirement.

```python
# The Agent requires an instance of a class implementing this interface:
from override_store import OverrideStore

# Initialization
override_store = YourDatabaseStore() # e.g., connecting to Redis or SQL
agent = GenderInferenceAgent(override_store=override_store)
```

### API Configuration

You must replace the placeholder values for the Face++ API in the `get_image_signal` method with your actual credentials to enable profile picture analysis.
