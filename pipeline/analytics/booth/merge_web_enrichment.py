"""
Merge web-researched candidate profiles into complete_candidate_data.json.

Run after research agents have produced enriched data:
  python -m analytics.merge_web_enrichment
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT = Path(__file__).parents[3]
OUTPUT_FILE = ROOT / "frontend" / "nextjs" / "app" / "myneta" / "complete_candidate_data.json"

# ── Web-researched profiles (from parallel research agents) ──────────────────
WEB_PROFILES: dict[str, dict] = {
    "ADITYANATH_2022": {
        "name": "Adityanath",
        "candidate_id": "ADITYANATH_2022",
        "party": "BJP",
        "ac_name": "Gorakhpur Urban",
        "ac_id": "GKP_322",
        "election_year": 2022,
        "profile": {
            "1_PersonalVitals": {
                "Full Name": "Ajay Mohan Singh Bisht (monastic name: Yogi Adityanath)",
                "Date of Birth": "5 June 1972",
                "Place of Birth": "Panchur village, Pauri Garhwal, Uttarakhand",
                "Age (2022)": "49",
                "Gender": "Male",
                "Caste": "Garhwali Rajput (Thakur)",
            },
            "2_FamilyEducation": {
                "Father": "Anand Singh Bisht (Forest Ranger, deceased)",
                "Mother": "Savitri Devi",
                "Spouse": "None (celibate Hindu monk)",
                "Spiritual Guru": "Mahant Avaidyanath (Gorakhnath Math)",
                "Education": "Bachelor of Science in Mathematics",
                "Institution": "HNB Garhwal University, Srinagar, Uttarakhand",
                "Religious Role": "Mahant (Head Priest) of Gorakhnath Math, Gorakhpur (since Sept 2014)",
            },
            "3_ConstituencyData": {
                "Constituency": "Gorakhpur Urban (AC No. 322)",
                "District": "Gorakhpur",
                "State": "Uttar Pradesh",
                "Total Registered Electors (2022)": "4,64,784",
                "Total Polling Stations": "471",
                "Voter Turnout (2022)": "53.85%",
                "Polling Date": "3 March 2022",
            },
            "4_PoliticalTrajectory": {
                "Party": "Bharatiya Janata Party (BJP)",
                "Previous Seats": "Gorakhpur Lok Sabha (5 consecutive terms: 1998, 1999, 2004, 2009, 2014)",
                "Current Role": "Chief Minister of Uttar Pradesh (2017–present; first UP CM to serve two full consecutive terms)",
                "Founded": "Hindu Yuva Vahini (2002)",
                "Youngest MP": "Youngest MP in 12th Lok Sabha (1998) at age 26",
            },
            "5_ElectoralRecord": {
                "Election": "UP Vidhan Sabha 2022 – Gorakhpur Urban AC-322",
                "Votes Received": "1,65,499",
                "Vote Share": "66.18%",
                "Runner-Up": "Subhawati Upendra Dutt Shukla (SP) — 62,109 votes (24.84%)",
                "Margin": "1,03,390 votes",
                "Result": "WON",
                "Note": "First Vidhan Sabha contest; previously 5-term Lok Sabha MP from Gorakhpur",
            },
            "6_FinancialProfile": {
                "Total Assets (2022 Affidavit)": "₹1,54,00,000 (approx. ₹1.54 crore)",
                "Movable Assets": "₹95,98,053 (cash, bank deposits, post office savings, vehicle, jewellery)",
                "Immovable Assets": "~₹58 lakh",
                "Liabilities": "Nil",
                "Annual Income (FY 2020-21)": "₹13,20,653",
                "Income Source": "Salary and allowances as People's Representative (former MP)",
            },
            "7_LegalCriminalRecord": {
                "Criminal Cases (2022 Affidavit)": "0 (None declared)",
                "Historical Cases": "3 cases in 2014 affidavit; all withdrawn or dismissed before 2022",
                "Notable": "20-year-old murder case dismissed by special court in 2019; 1995 case withdrawn after becoming CM",
                "Status": "Clean affidavit for 2022 election",
            },
            "8_CareerProfession": {
                "Profession": "Social & Religious Work; Salary/Allowances as People's Representative",
                "Career Summary": "Disciple of Mahant Avaidyanath; elected MP from Gorakhpur 1998 at age 26; 5 Lok Sabha terms (1998–2014); founded Hindu Yuva Vahini (2002); became Mahant of Gorakhnath Math (Sept 2014); appointed CM of UP on 19 March 2017; won first Vidhan Sabha from Gorakhpur Urban 2022; re-appointed CM for second term — UP's longest-serving CM.",
            },
            "9_PublicPresencePolicy": {
                "Key Policies": "Bulldozer justice; Anti-Romeo squads; Crackdown on illegal slaughterhouses; CAA; UP Expressway expansion; UP Global Investors Summit; Mahakumbh 2025",
                "Public Perception": "Polarising — 'Bulldozer Baba' for supporters (law & order); critics allege extrajudicial encounters and communal politics",
                "Nickname": "Bulldozer Baba",
                "Ideology": "Hindutva, Hindu nationalism, BJP right wing",
            },
            "10_DigitalPresence": {
                "Twitter/X Handle": "@myogiadityanath",
                "Twitter/X Followers": "~32.6 million (crossed 25M in June 2023)",
                "Facebook": "facebook.com/MYogiAdityanath",
                "Facebook Followers": "~12 million (most-followed Indian CM on Facebook)",
                "Instagram": "@myogi_adityanath",
                "Instagram Followers": "~17 million (crossed 7M / 70 lakh in October 2023)",
                "YouTube": "youtube.com/mahantyogiadityanath",
                "YouTube Subscribers": "~787,000",
                "Website": "yogiadityanath.in",
                "Wikipedia": "https://en.wikipedia.org/wiki/Yogi_Adityanath",
                "Total Digital Reach": "~62+ million across all platforms",
            },
        },
    },
    "SUBHAWATI_UPENDRA_DUTT_SHUKLA_2022": {
        "name": "Subhawati Upendra Dutt Shukla",
        "candidate_id": "SUBHAWATI_UPENDRA_DUTT_SHUKLA_2022",
        "party": "Samajwadi Party",
        "ac_name": "Gorakhpur Urban",
        "ac_id": "GKP_322",
        "election_year": 2022,
        "profile": {
            "1_PersonalVitals": {
                "Full Name": "Subhawati Upendra Dutt Shukla (also: Sabhawati / Subhavati Shukla)",
                "Place of Birth": "Gorakhpur, Uttar Pradesh",
                "Gender": "Female",
                "Caste": "Brahmin",
            },
            "2_FamilyEducation": {
                "Husband": "Late Upendra Dutt Shukla (BJP Vice President, UP; died May 2020, cardiac arrest)",
                "Sons": "Arvind Dutt Shukla and Amit Dutt Shukla (both joined SP with mother in Jan 2022)",
                "Status": "Widow",
                "Education": "Literate",
                "Profession (Declared)": "Housewife",
            },
            "3_ConstituencyData": {
                "Constituency": "Gorakhpur Urban (AC No. 322)",
                "District": "Gorakhpur",
                "Total Registered Electors (2022)": "4,64,784",
                "Voter Turnout (2022)": "53.85%",
            },
            "4_PoliticalTrajectory": {
                "Party": "Samajwadi Party (SP)",
                "Joined SP": "January 2022 (along with both sons)",
                "Previous Party Affiliation": "None directly; husband was senior UP BJP VP",
                "Candidacy Strategy": "SP fielded her — a Brahmin widow of a BJP stalwart — to split BJP's Brahmin vote against Thakur CM Yogi",
            },
            "5_ElectoralRecord": {
                "Election": "UP Vidhan Sabha 2022 – Gorakhpur Urban AC-322",
                "Votes Received": "~62,109",
                "Vote Share": "24.84%",
                "Winner": "Yogi Adityanath (BJP) — 1,65,499 votes (66.18%)",
                "Margin Lost By": "1,03,390 votes",
                "Result": "LOST (Runner-Up / 2nd place)",
            },
            "6_FinancialProfile": {
                "Total Assets (2022 Affidavit)": "₹1,95,00,000+ (more than ₹1.95 crore)",
                "Income Source": "Housewife (no declared professional income)",
                "Affidavit": "myneta.info/Uttarpradesh2022/candidate.php?candidate_id=3799",
            },
            "7_LegalCriminalRecord": {
                "Criminal Cases": "0 (None declared)",
                "Status": "Clean affidavit",
            },
            "8_CareerProfession": {
                "Profession": "Housewife",
                "Career Summary": "Wife of late UP BJP VP Upendra Dutt Shukla. After his death (May 2020), she and her two sons joined SP (Jan 2022). SP fielded her from Gorakhpur Urban against sitting CM Yogi Adityanath as a Brahmin face. She contested and lost in her debut election.",
            },
            "9_PublicPresencePolicy": {
                "Key Policies": "SP platform: social justice, anti-incumbency, Brahmin outreach",
                "Public Perception": "Sympathy candidate leveraging late husband's Brahmin political legacy; SP's strategic Brahmin counter to Yogi's Thakur identity",
            },
            "10_DigitalPresence": {
                "Twitter/X Handle": "Not found",
                "Facebook": "Not found",
                "Instagram": "Not found",
                "Digital Footprint": "No significant verified digital presence",
            },
        },
    },
    "DR_CHETNA_PANDEY_2022": {
        "name": "Dr. Chetna Pandey",
        "candidate_id": "DR_CHETNA_PANDEY_2022",
        "party": "INC",
        "ac_name": "Gorakhpur Urban",
        "ac_id": "GKP_322",
        "election_year": 2022,
        "profile": {
            "1_PersonalVitals": {
                "Full Name": "Dr. Chetna Pandey",
                "Place of Birth": "Gorakhpur, Uttar Pradesh",
                "Gender": "Female",
                "Father": "Ram Datt Pandey",
            },
            "2_FamilyEducation": {
                "Education": "Ph.D. (Hindi), M.A., B.Ed., B.J. (Journalism), Sangeet Prabhakar",
                "Institution": "Deen Dayal Upadhyay University (DDU), Gorakhpur — Ph.D. awarded 2010",
                "Additional": "Gold medal awardee for poetry and tabla recitals",
            },
            "3_ConstituencyData": {
                "Constituency": "Gorakhpur Urban",
                "District": "Gorakhpur",
                "AC Number": "322",
            },
            "4_PoliticalTrajectory": {
                "Party": "Indian National Congress (INC)",
                "Prior Elections": "2012 UP Vidhan Sabha — contested from Sahajanwa (Gorakhpur) as Independent; lost",
                "Party History": "Former ABVP member; former VP of DDU Gorakhpur Students' Union; joined INC ~2019",
            },
            "5_ElectoralRecord": {
                "Election": "2022 UP Vidhan Sabha",
                "Votes Received": "~2,876",
                "Vote Share": "~1.15%",
                "Result": "Lost — forfeited security deposit",
                "Winner": "Yogi Adityanath (BJP) — 1,65,499 votes (66.18%)",
            },
            "6_FinancialProfile": {
                "Affidavit": "myneta.info/uttarpradesh2022/candidate.php?candidate_id=3809"
            },
            "7_LegalCriminalRecord": {"Criminal Cases": "None reported", "Status": "Clean"},
            "8_CareerProfession": {
                "Profession": "Social Worker; Poet; Academic (Hindi literature)",
                "Career Summary": "Doctorate in Hindi literature from DDU Gorakhpur (2010). Published poetry collections: 'Chetna Ke Geet' and 'Geet Aur Msutak'. Renowned soprano at kavi sammelans and mushairas. Tabla virtuoso with national & international accolades. INC candidate against CM Yogi in 2022.",
            },
            "9_PublicPresencePolicy": {
                "Key Policies": "Social welfare; women's empowerment; arts and cultural promotion",
                "Media Coverage": "Featured in Outlook India as 'A Poet, A Tabla Player, And Yogi's Challenger'",
            },
            "10_DigitalPresence": {
                "Twitter/X Handle": "@iamchetnapande",
                "Facebook": "facebook.com/DrChetnaPandey / facebook.com/iamchetnapande",
                "Instagram": "Not found",
                "Website": "Not found",
                "Digital Footprint": "Active Facebook presence; Twitter handle @iamchetnapande; moderate local digital presence",
            },
        },
    },
    "KHWAJA_SHAMSUDDIN_2022": {
        "name": "Khwaja Shamsuddin",
        "candidate_id": "KHWAJA_SHAMSUDDIN_2022",
        "party": "BSP",
        "ac_name": "Gorakhpur Urban",
        "ac_id": "GKP_322",
        "election_year": 2022,
        "profile": {
            "1_PersonalVitals": {
                "Full Name": "Khwaja Shamsuddin",
                "Place of Birth": "Gorakhpur, Uttar Pradesh",
                "Gender": "Male",
                "Religion": "Muslim",
                "Voter Roll": "Gorakhpur Rural constituency, Serial No. 83, Part No. 64",
            },
            "2_FamilyEducation": {
                "Spouse": "Housewife",
                "Education": "10th Pass (High School)",
                "Institution": "P.H. Secondary School, Amdhari Nighauri, Siddharthnagar",
            },
            "3_ConstituencyData": {
                "Constituency": "Gorakhpur Urban",
                "District": "Gorakhpur",
                "AC Number": "322",
            },
            "4_PoliticalTrajectory": {
                "Party": "Bahujan Samaj Party (BSP)",
                "Role": "BSP Sector In-charge, Gorakhpur district; Head of BSP Muslim Bhaichara Committee",
                "Party History": "20 years of active BSP ground work in Gorakhpur district; first-time Vidhan Sabha contestant in 2022",
            },
            "5_ElectoralRecord": {
                "Election": "2022 UP Vidhan Sabha",
                "Votes Received": "~6,367 – 8,024 (conflicting sources)",
                "Vote Share": "~3.21%",
                "Result": "Lost — forfeited security deposit",
            },
            "6_FinancialProfile": {
                "Affidavit": "myneta.info/uttarpradesh2022/candidate.php?candidate_id=3800"
            },
            "7_LegalCriminalRecord": {"Criminal Cases": "None reported", "Status": "Clean"},
            "8_CareerProfession": {
                "Profession": "Trader (self-declared 'Private Work')",
                "Career Summary": "Trader by profession. 20-year BSP veteran and Gorakhpur district sector in-charge. Head of BSP Muslim Bhaichara Committee. Previously contested local body elections on BSP ticket. First-time assembly candidate in 2022.",
            },
            "9_PublicPresencePolicy": {
                "Key Policies": "BSP Bahujan ideology; Muslim community mobilisation; social justice",
                "Public Perception": "Long-standing BSP loyalist and grassroots worker; minority community representative",
            },
            "10_DigitalPresence": {
                "Twitter/X Handle": "Not found",
                "Facebook": "facebook.com/p/Khwaja-Shamsuddin-BSP-Leader-100068743971597/ (BSP Leader page)",
                "Instagram": "Not found",
                "Website": "Not found",
                "Digital Footprint": "Minimal; one Facebook page identified; no significant independent web presence",
            },
        },
    },
    "CHANDRA_SHEKHAR_2022": {
        "name": "Chandra Shekhar",
        "candidate_id": "CHANDRA_SHEKHAR_2022",
        "party": "AAZAD SAMAJ PARTY (KANSHI RAM)",
        "ac_name": "Gorakhpur Urban",
        "ac_id": "GKP_322",
        "election_year": 2022,
        "profile": {
            "1_PersonalVitals": {
                "Full Name": "Chandrashekhar Azad 'Ravan'",
                "Date of Birth": "3 December 1986",
                "Place of Birth": "Village Chhutmalpur, Saharanpur, Uttar Pradesh",
                "Gender": "Male",
                "Caste": "Jatav (Dalit/Scheduled Caste)",
                "Age (2022)": "35",
            },
            "2_FamilyEducation": {
                "Father": "Govardhan Das (retired Principal, government school)",
                "Education": "Bachelor of Arts (BA), LLB",
                "Institution": "HNB Garhwal University",
                "Additional": "Practicing lawyer; legal background used in Dalit rights activism",
            },
            "3_ConstituencyData": {
                "Constituency": "Gorakhpur Urban",
                "District": "Gorakhpur",
                "AC Number": "322",
            },
            "4_PoliticalTrajectory": {
                "Party": "Aazad Samaj Party (Kanshi Ram) — ASP",
                "Role": "National President, ASP; Founder & Chief, Bhim Army",
                "Prior Elections": "2022 Gorakhpur Urban — first Vidhan Sabha contest",
                "Subsequent": "Won 2024 Lok Sabha from Nagina (UP) by 1,51,473 vote margin; currently serving as MP",
                "Founded": "Bhim Army (2014/2015); Aazad Samaj Party (Kanshi Ram) on 15 March 2020",
                "Recognition": "TIME Magazine 100 Emerging Leaders (February 2021)",
            },
            "5_ElectoralRecord": {
                "Election": "2022 UP Vidhan Sabha",
                "Votes Received": "~7,454",
                "Vote Share": "~2.98%",
                "Result": "Lost — forfeited security deposit",
                "2024 LS Result": "Won Nagina Lok Sabha seat (2024 general election); margin 1,51,473 votes",
            },
            "6_FinancialProfile": {
                "Affidavit": "myneta.info/uttarpradesh2022/candidate.php?candidate_id=3802"
            },
            "7_LegalCriminalRecord": {
                "Criminal Cases": "Multiple declared in 2022 affidavit: IPC 332 (voluntarily causing hurt to deter public servant) × 4; mischief by fire/explosive × 4",
                "Status": "Pending — widely reported as politically motivated, related to Dalit rights agitation",
                "Note": "Jailed multiple times in connection with anti-caste violence protests",
            },
            "8_CareerProfession": {
                "Profession": "Lawyer; Political Activist; Ambedkarite leader",
                "Career Summary": "Born Jatav (Dalit), Saharanpur. Pursued BA + LLB from Garhwal University. Co-founded Bhim Army (2014–15) for Dalit rights through education & legal means. Rose to national prominence after Saharanpur caste violence (2017). Founded Aazad Samaj Party (Kanshi Ram) on 15 March 2020. Contested 2022 Vidhan Sabha from Gorakhpur Urban against CM Yogi; lost deposit. Won 2024 Lok Sabha from Nagina as MP. Currently MP in 18th Lok Sabha.",
            },
            "9_PublicPresencePolicy": {
                "Key Policies": "Dalit empowerment; Ambedkarite social justice; anti-caste discrimination; constitutional rights for SCs/STs; opposition to CAA/NRC; Bhim Pathashalas community schools",
                "Public Perception": "One of India's most prominent young Dalit leaders; TIME Magazine 100 Emerging Leaders 2021; 'every party is wary of' — multiple media outlets",
            },
            "10_DigitalPresence": {
                "Twitter/X Handle": "@BhimArmyChief",
                "Twitter/X Followers": "Large national presence (exact count varies)",
                "Facebook": "facebook.com/BhimArmyChief",
                "Facebook Followers": "~1.4 million",
                "Instagram": "@bhimarmychief",
                "Instagram Followers": "~3 million",
                "Website": "azadsamajparty.org",
                "Digital Footprint": "Very high — one of India's most-followed Dalit political leaders on social media; verified presence on all major platforms",
            },
        },
    },
    "DR_RADHA_MOHAN_DAS_AGRAWAL_2017_2017": {
        "name": "Dr. Radha Mohan Das Agrawal",
        "candidate_id": "DR_RADHA_MOHAN_DAS_AGRAWAL_2017_2017",
        "party": "BJP",
        "ac_name": "Gorakhpur Urban",
        "ac_id": "GKP_322",
        "election_year": 2017,
        "profile": {
            "1_PersonalVitals": {
                "Full Name": "Dr. Radha Mohan Das Agrawal",
                "Date of Birth": "6 March 1955",
                "Place of Birth": "Gorakhpur, Uttar Pradesh",
                "Gender": "Male",
                "Caste": "Agrawal (Vaishya)",
            },
            "2_FamilyEducation": {
                "Father": "Late Shri Dau Das Agrawal",
                "Spouse": "Ragini Agrawal (married 20 January 1988)",
                "Children": "One daughter (pediatrician)",
                "Education": "MBBS (1976), MD Pediatrics (1981)",
                "Institution": "Banaras Hindu University (BHU), Varanasi",
                "Additional": "Former Asst. Professor BHU; President, Junior Doctors Assoc. (1974); RSS/ABVP since college",
            },
            "3_ConstituencyData": {
                "Constituency": "Gorakhpur Urban",
                "District": "Gorakhpur",
                "AC Number": "322",
                "Total Electors (2017)": "4,29,226",
                "Total Valid Votes (2017)": "2,18,831",
            },
            "4_PoliticalTrajectory": {
                "Party": "BJP (contested 2002 on Hindu Mahasabha ticket; joined BJP before 2007)",
                "Current Role": "Member of Parliament, Rajya Sabha, UP (2022–2028); National General Secretary, BJP (since 30 Jan 2023); Chairman, Parliamentary Standing Committee on Home Affairs",
                "MLA Terms": "4 terms from Gorakhpur Urban — 2002 (Hindu Mahasabha), 2007, 2012, 2017 (all BJP). Vacated seat for CM Yogi Adityanath's 2022 contest.",
                "MP Terms": "Rajya Sabha MP from UP since 5 July 2022 (won unopposed on BJP nomination 31 May 2022)",
            },
            "5_ElectoralRecord": {
                "2002 Vidhan Sabha": "Won — Gorakhpur Urban (Hindu Mahasabha)",
                "2007 Vidhan Sabha": "Won — Gorakhpur Urban (BJP)",
                "2012 Vidhan Sabha": "Won — Gorakhpur Urban (BJP); margin ~48,000 votes",
                "2017 Votes": "1,22,221",
                "2017 Vote Share": "~55.85%",
                "2017 Margin": "60,730 votes (over INC's Rana Rahul Singh with 61,491 votes)",
                "2017 Result": "Won",
                "2022": "Did not contest; vacated for CM Yogi (BJP). Won Rajya Sabha 2022 unopposed.",
            },
            "6_FinancialProfile": {
                "Total Assets (2017 Affidavit)": "₹3,18,79,393 (approx. ₹3.19 crore)",
                "Liabilities": "₹2,02,000",
                "Affidavit": "myneta.info/uttarpradesh2017/candidate.php?candidate_id=4488",
            },
            "7_LegalCriminalRecord": {
                "Criminal Cases (2017 Affidavit)": "Multiple IPC: 147, 153, 153A, 295, 323, 352, 427, 436, 447, 452",
                "Status": "Acquitted in case under IPC 147/323/352/447 on 4 April 2023; two other cases dropped. No conviction on record.",
                "Note": "BJP issued notice in 2019 for sharing objectionable posts",
            },
            "8_CareerProfession": {
                "Profession": "Medical Doctor (Pediatrician) and Politician",
                "Career Summary": "Trained pediatrician (MBBS 1976, MD 1981 BHU). Former Asst. Professor BHU. RSS/ABVP since student days. Entered politics in 2002. Built 20+ year dominance over Gorakhpur Urban (4 consecutive Vidhan Sabha terms) before elevation to Rajya Sabha (2022). Appointed BJP National General Secretary (January 2023).",
            },
            "9_PublicPresencePolicy": {
                "Key Policies": "Hindu nationalist positions aligned with BJP/RSS; healthcare & development in Gorakhpur; national security; active critic of Congress/SP in Parliament",
                "Public Perception": "Popular, approachable grassroots leader in Gorakhpur; known for direct voter engagement. Key BJP face in eastern UP. Elevation to Rajya Sabha and BJP National GS seen as major organisational reward.",
            },
            "10_DigitalPresence": {
                "Twitter/X Handle": "@AgrawalRMD",
                "Twitter/X Followers": "~28,500",
                "Twitter/X Joined": "January 2013",
                "Facebook": "facebook.com/agrawalrmdmla",
                "Facebook Followers": "~38,000 followers",
                "Instagram": "@dr_radhamohandasagrawal",
                "Website": "bjp.org/dr-radha-mohan-das-agarwal (BJP official profile)",
                "Wikipedia": "https://en.wikipedia.org/wiki/Radha_Mohan_Das_Agarwal",
                "Digital Footprint": "Moderately active — regular posts on X (political commentary, party positions, parliamentary work) and Facebook.",
            },
        },
    },
    "JANARDAN_CHOUDHARI_2017": {
        "name": "Janardan Choudhari",
        "candidate_id": "JANARDAN_CHOUDHARI_2017",
        "party": "BSP",
        "ac_name": "Gorakhpur Urban",
        "ac_id": "GKP_322",
        "election_year": 2017,
        "profile": {
            "1_PersonalVitals": {
                "Full Name": "Janardan Choudhari",
                "Gender": "Male",
                "Place of Birth": "Gorakhpur region, Uttar Pradesh",
            },
            "2_FamilyEducation": {"Education": "Not publicly available"},
            "3_ConstituencyData": {
                "Constituency": "Gorakhpur Urban",
                "District": "Gorakhpur",
                "AC Number": "322",
            },
            "4_PoliticalTrajectory": {
                "Party": "BSP (Bahujan Samaj Party)",
                "Role": "BSP candidate / local party functionary in Gorakhpur",
            },
            "5_ElectoralRecord": {
                "2017 Votes": "24,297",
                "2017 Vote Share": "~11.1%",
                "2017 Result": "Lost (3rd place)",
                "2017 Positions": "BJP won with 1,22,221; INC 2nd with 61,491; BSP 3rd with 24,297",
            },
            "6_FinancialProfile": {"Assets": "Not publicly available"},
            "7_LegalCriminalRecord": {"Criminal Cases": "Not publicly available"},
            "8_CareerProfession": {
                "Profession": "Not publicly available",
                "Career Summary": "Local BSP leader/candidate from Gorakhpur Urban. Contested 2017 UP Vidhan Sabha as BSP nominee, finishing 3rd with 24,297 votes (11.1%). No further public record of significant political office found.",
            },
            "9_PublicPresencePolicy": {
                "Key Policies": "BSP platform — Dalit rights, social justice, Ambedkarite ideology"
            },
            "10_DigitalPresence": {
                "Twitter/X Handle": "Not found",
                "Facebook": "Not found",
                "Instagram": "Not found",
                "Digital Footprint": "No significant digital presence found in public search results",
            },
        },
    },
    "VIJAY_KUMAR_SRIVASTAVA_2022": {
        "name": "Vijay Kumar Srivastava",
        "candidate_id": "VIJAY_KUMAR_SRIVASTAVA_2022",
        "party": "AAP",
        "ac_name": "Gorakhpur Urban",
        "ac_id": "GKP_322",
        "election_year": 2022,
        "profile": {
            "1_PersonalVitals": {
                "Full Name": "Vijay Kumar Srivastava",
                "Gender": "Male",
                "Place of Birth": "Gorakhpur, Uttar Pradesh",
            },
            "2_FamilyEducation": {
                "Spouse": "Government service employee",
                "Education": "Not publicly confirmed",
            },
            "3_ConstituencyData": {
                "Constituency": "Gorakhpur Urban",
                "District": "Gorakhpur",
                "AC Number": "322",
            },
            "4_PoliticalTrajectory": {
                "Party": "Aam Aadmi Party (AAP)",
                "Role": "Candidate; local social activist and contractor",
                "Nomination": "Named in AAP's 5th candidate list (29 Jan 2022); endorsed by AAP MP Sanjay Singh as 'well-known face in Gorakhpur Sadar'",
            },
            "5_ElectoralRecord": {
                "Election": "2022 UP Vidhan Sabha",
                "Vote Share": "<1% (estimated)",
                "Result": "Lost — forfeited security deposit",
            },
            "6_FinancialProfile": {
                "Profession": "Unregistered Contractor (self-declared)",
                "Affidavit": "myneta.info/uttarpradesh2022/candidate.php?candidate_id=3810",
            },
            "7_LegalCriminalRecord": {"Criminal Cases": "None reported"},
            "8_CareerProfession": {
                "Profession": "Unregistered Contractor; Social Worker",
                "Career Summary": "Local contractor and social activist in Gorakhpur. Described by AAP leader Sanjay Singh as having worked with several social organisations and 'been fighting for people's causes for a long time in Gorakhpur Sadar'. Fielded by AAP for 2022 Vidhan Sabha; lost deposit.",
            },
            "9_PublicPresencePolicy": {
                "Key Policies": "AAP: anti-corruption, free electricity, quality education, healthcare, good governance"
            },
            "10_DigitalPresence": {
                "Twitter/X Handle": "Not found",
                "Facebook": "Not found",
                "Instagram": "Not found",
                "Digital Footprint": "No public social media presence identified; essentially no independent digital footprint beyond election news mentions",
            },
        },
    },
}


def run() -> None:
    existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    logger.info("Loaded %d existing profiles", len(existing))

    updated = 0
    added = 0

    for key, profile in WEB_PROFILES.items():
        if key in existing:
            # Merge — web research overrides existing sections
            for section, fields in profile["profile"].items():
                existing[key]["profile"][section] = fields
            updated += 1
            logger.info("Updated: %s", key)
        else:
            existing[key] = profile
            added += 1
            logger.info("Added: %s", key)

    # Ensure every profile has 10_DigitalPresence (add default if missing)
    for key, profile in existing.items():
        if "10_DigitalPresence" not in profile.get("profile", {}):
            profile["profile"]["10_DigitalPresence"] = {
                "Twitter/X Handle": "Not found",
                "Facebook": "Not found",
                "Instagram": "Not found",
                "YouTube": "Not found",
                "Website": "Not found",
                "Wikipedia": "Not found",
                "Digital Footprint": "No public digital presence indexed for this candidate.",
            }
            logger.info("Added default DigitalPresence for: %s", key)

    OUTPUT_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Done — %d updated, %d added, %d total profiles", updated, added, len(existing))


if __name__ == "__main__":
    run()
