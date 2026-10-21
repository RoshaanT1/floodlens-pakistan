# Model A analysis (validation, 1 Jul to 31 Dec 2025)

Model: `gbm` (18 features), probabilities cross-fitted on validation. Brier at 24 h with 95% day-block bootstrap intervals; BSS = 1 - Brier / climatology Brier. Validation-stage results, not test results.

## A5: groups

| Grouping | Group | Rows | Events | Model Brier [95% CI] | Climatology Brier | BSS |
| --- | --- | --- | --- | --- | --- | --- |
| province | Azad Kashmir | 1840 | 58 | 0.0299 [0.0179, 0.0443] | 0.0304 | +0.015 |
| province | Balochistan | 6440 | 127 | 0.0182 [0.0127, 0.0247] | 0.0190 | +0.045 |
| province | Gilgit Baltistan | 2576 | 83 | 0.0276 [0.0179, 0.0409] | 0.0301 | +0.084 |
| province | Islamabad | 184 | 9 | 0.0444 [0.0217, 0.0715] | 0.0458 | +0.032 |
| province | Khyber Pakhtunkhwa | 6440 | 230 | 0.0310 [0.0213, 0.0428] | 0.0336 | +0.076 |
| province | Punjab | 6624 | 221 | 0.0296 [0.0207, 0.0409] | 0.0314 | +0.059 |
| province | Sindh | 5336 | 44 | 0.0073 [0.0037, 0.0110] | 0.0083 | +0.120 |
| terrain | mountain | 10304 | 338 | 0.0287 [0.0210, 0.0383] | 0.0309 | +0.070 |
| terrain | plain | 19136 | 434 | 0.0204 [0.0155, 0.0258] | 0.0217 | +0.060 |
| coast | coastal | 2208 | 29 | 0.0117 [0.0060, 0.0193] | 0.0126 | +0.070 |
| coast | inland | 27232 | 743 | 0.0243 [0.0185, 0.0310] | 0.0259 | +0.064 |
| 2022 flooding | flood-prone | 6072 | 72 | 0.0107 [0.0070, 0.0148] | 0.0118 | +0.087 |
| 2022 flooding | not flood-prone | 23368 | 700 | 0.0266 [0.0201, 0.0342] | 0.0283 | +0.062 |
| season | dry (Oct-Dec) | 14720 | 129 | 0.0079 [0.0037, 0.0125] | 0.0087 | +0.093 |
| season | monsoon (Jun-Sep) | 14720 | 643 | 0.0388 [0.0295, 0.0478] | 0.0412 | +0.058 |

**Weakest group** (lowest BSS among groups with at least 5 events): province = Azad Kashmir, BSS +0.015.

## A6: Buner, 14 and 15 Aug 2025

Flag rule: probability >= 0.5. Hit = flagged on a day whose label is 1.

| Day | Lead | Forecast rain (mm, centroid) | Threshold (mm) | Observed wettest pixel (mm) | Label | Model p | Climatology p | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-14 | 1 | 10.6 | 57.5 | 25.5 | 0 | 0.136 | 0.039 | correct quiet |
| 2025-08-14 | 2 | 14.8 | 57.5 | 25.5 | 0 | 0.196 | 0.039 | correct quiet |
| 2025-08-14 | 3 | 16.4 | 57.5 | 25.5 | 0 | 0.170 | 0.039 | correct quiet |
| 2025-08-15 | 1 | 24.9 | 57.5 | 43.2 | 0 | 0.153 | 0.039 | correct quiet |
| 2025-08-15 | 2 | 10.8 | 57.5 | 43.2 | 0 | 0.129 | 0.039 | correct quiet |
| 2025-08-15 | 3 | 2.1 | 57.5 | 43.2 | 0 | 0.129 | 0.039 | correct quiet |

## E2: model flags vs NDMA sitreps, Jul to Sep 2025

Districts flagged at least once at 24 h (p >= 0.5): 1. Districts named in at least one NDMA monsoon 2025 sitrep: 125.

- both: 1 (Diamir)
- flagged, not named by NDMA: 0 (none)
- named by NDMA, never flagged: 124 (Abbottabad, Astore, Attock, Awaran, Badin, Bagh, Bahawalnagar, Bahawalpur, Bajaur, Bannu, Barkhan, Batagram, Bhakkar, Bhimber, Buner, Central Karachi, Chakwal, Charsadda, Chiniot, Chitral Upper, Dadu, Dera Bugti, Dera Ghazi Khan, Duki, East Karachi, Faisalabad, Ghanche, Ghizer, Gilgit, Gujranwala, Gujrat, Hafizabad, Hangu, Haripur, Harnai, Haveli, Hunza, Hyderabad, Islamabad, Jacobabad, Jhal Magsi, Jhang, Jhelum, Jhelum Valley, Kachhi, Kalat, Karak, Kashmore, Kasur, Khairpur, Khanewal, Kharmang, Khushab, Khuzdar, Khyber, Killa Saifullah, Kohat, Kohistan Lower, Kohlu, Kotli, Kurram, Lahore, Lakki Marwat, Larkana, Lehri, Lodhran, Loralai, Lower Dir, Malakand, Mandi Bahauddin, Mansehra, Mardan, Matiari, Mianwali, Mirpur, Mirpur Khas, Mohmand, Multan, Musakhel, Muzaffarabad, Muzaffargarh, Nagar, Nankana Sahib, Narowal, Neelum, North Waziristan, Nowshera, Okara, Pakpattan, Peshawar, Poonch, Rahim Yar Khan, Rajanpur, Rawalpindi, Sahiwal, Sargodha, Shangla, Sheikhupura, Sherani, Shigar, Shikarpur, Sialkot, Sibi, Skardu, South Karachi, South Waziristan, Sudhnoti, Sujawal, Sukkur, Swabi, Swat, Tando Allahyar, Tando Muhammad Khan, Tank, Tharparkar, Toba Tek Singh, Tor Ghar, Umer Kot, Upper Dir, Vehari, Washuk, West Karachi, Zhob, Ziarat)

NDMA naming a district means it reported impacts or warnings there, not that rain crossed our threshold, so this is a sense check, not a score. Districts named in every sitrep (Islamabad, Lahore, Rawalpindi on 21 Oct) are mostly boilerplate (NDMA's address, rainfall station tables), not impact reports.
