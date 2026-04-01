import React, { useState } from "react";
import {
  LineChart, BarChart, Line, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, CartesianGrid, Cell
} from "recharts";

// Embedded data — generated from outputs/dashboard_demo_data.json
const DATA = {
  "summary": {
    "snapshot_date": "2025-12-15",
    "month": "2025-12",
    "model_used": "GradientBoosting",
    "total_pipeline_loans": 1109,
    "total_pipeline_value": 314082997.0,
    "live_pipeline_loans": 708,
    "live_pipeline_value": 146986672.0,
    "dead_pipeline_loans": 401,
    "dead_pipeline_value": 167096325.0,
    "already_funded_loans": 156,
    "already_funded_value": 68191001.0,
    "projected_total": 100618756.73,
    "overall_pull_through": 0.3903,
    "median_cycle_days": 29.0,
    "elimination_stats": {
      "total": 1109,
      "eliminated": 401,
      "pct_eliminated": 36.2,
      "by_reason": {
        "opened_stale": 285,
        "underwriting_unlocked_stale": 52,
        "approved_expired_lock": 43,
        "submitted_unlocked_stale": 17,
        "application_stale": 4
      }
    }
  },
  "liveLoans": [
    {
      "loan_guid": "82509113",
      "loan_amount": 2088856.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Cond Review",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9117,
      "expected_value": 1904448.56,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511086",
      "loan_amount": 1860000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "CTC",
      "days_at_stage": 19,
      "is_locked": true,
      "ml_probability": 0.8668,
      "expected_value": 1612231.46,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511184",
      "loan_amount": 1074500.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Docs",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.992,
      "expected_value": 1065951.92,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511212",
      "loan_amount": 1461225.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 25,
      "is_locked": true,
      "ml_probability": 0.6193,
      "expected_value": 904872.07,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511163",
      "loan_amount": 875000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Fund Cond",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9902,
      "expected_value": 866461.42,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82507258",
      "loan_amount": 974650.0,
      "product_type": "FHA",
      "current_stage": "Approved",
      "days_at_stage": 151,
      "is_locked": true,
      "ml_probability": 0.821,
      "expected_value": 800140.4,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82506076",
      "loan_amount": 750000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Docs",
      "days_at_stage": 3,
      "is_locked": true,
      "ml_probability": 0.9924,
      "expected_value": 744309.32,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511217",
      "loan_amount": 840000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 27,
      "is_locked": true,
      "ml_probability": 0.8447,
      "expected_value": 709567.8,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82506079",
      "loan_amount": 698000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "CTC",
      "days_at_stage": 5,
      "is_locked": true,
      "ml_probability": 0.9869,
      "expected_value": 688887.66,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511078",
      "loan_amount": 1137750.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 38,
      "is_locked": true,
      "ml_probability": 0.5823,
      "expected_value": 662514.78,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510624",
      "loan_amount": 4000000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 46,
      "is_locked": false,
      "ml_probability": 0.1645,
      "expected_value": 657896.3,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510731",
      "loan_amount": 616000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "CTC",
      "days_at_stage": 7,
      "is_locked": true,
      "ml_probability": 0.9677,
      "expected_value": 596128.87,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510734",
      "loan_amount": 595000.0,
      "product_type": "CONFORMING",
      "current_stage": "Fund Cond",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9906,
      "expected_value": 589407.99,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511142",
      "loan_amount": 604000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Final UW",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9531,
      "expected_value": 575691.86,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511164",
      "loan_amount": 583000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Final UW",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9506,
      "expected_value": 554209.16,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510338",
      "loan_amount": 695000.0,
      "product_type": "VA",
      "current_stage": "Cond Review",
      "days_at_stage": 14,
      "is_locked": true,
      "ml_probability": 0.7894,
      "expected_value": 548634.28,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510421",
      "loan_amount": 589033.0,
      "product_type": "NONCONFORMING",
      "current_stage": "CTC",
      "days_at_stage": 3,
      "is_locked": true,
      "ml_probability": 0.9298,
      "expected_value": 547671.7,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511316",
      "loan_amount": 1950000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 29,
      "is_locked": false,
      "ml_probability": 0.2695,
      "expected_value": 525603.43,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511196",
      "loan_amount": 781650.0,
      "product_type": "FHA",
      "current_stage": "Approved",
      "days_at_stage": 29,
      "is_locked": true,
      "ml_probability": 0.6698,
      "expected_value": 523557.96,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510332",
      "loan_amount": 500000.0,
      "product_type": "2ND",
      "current_stage": "Fund Cond",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9648,
      "expected_value": 482377.72,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511124",
      "loan_amount": 700000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 33,
      "is_locked": true,
      "ml_probability": 0.6889,
      "expected_value": 482248.57,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82509010",
      "loan_amount": 2240000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 101,
      "is_locked": true,
      "ml_probability": 0.2133,
      "expected_value": 477758.8,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511199",
      "loan_amount": 500000.0,
      "product_type": "2ND",
      "current_stage": "Final UW",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9443,
      "expected_value": 472133.01,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511189",
      "loan_amount": 500000.0,
      "product_type": "2ND",
      "current_stage": "Final UW",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9341,
      "expected_value": 467070.96,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511178",
      "loan_amount": 588000.0,
      "product_type": "CONVENTIONAL BOND STD MI",
      "current_stage": "Cond Review",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.7561,
      "expected_value": 444582.31,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510569",
      "loan_amount": 450000.0,
      "product_type": "FHA",
      "current_stage": "CTC",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9483,
      "expected_value": 426716.11,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510740",
      "loan_amount": 800250.0,
      "product_type": "CONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 35,
      "is_locked": true,
      "ml_probability": 0.5255,
      "expected_value": 420554.03,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511329",
      "loan_amount": 412000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Docs",
      "days_at_stage": 5,
      "is_locked": true,
      "ml_probability": 0.9889,
      "expected_value": 407427.65,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510539",
      "loan_amount": 432000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Final UW",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.8978,
      "expected_value": 387842.77,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511270",
      "loan_amount": 404000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "CTC",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9581,
      "expected_value": 387077.82,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511325",
      "loan_amount": 381175.0,
      "product_type": "FHA",
      "current_stage": "Fund Cond",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9841,
      "expected_value": 375133.22,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511289",
      "loan_amount": 372000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Docs",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9931,
      "expected_value": 369414.67,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511323",
      "loan_amount": 376000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Cond Review",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9521,
      "expected_value": 358007.01,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510346",
      "loan_amount": 360000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Docs",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9874,
      "expected_value": 355467.86,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510625",
      "loan_amount": 357000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Fund Cond",
      "days_at_stage": 5,
      "is_locked": true,
      "ml_probability": 0.9886,
      "expected_value": 352927.92,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511343",
      "loan_amount": 504000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 26,
      "is_locked": true,
      "ml_probability": 0.6893,
      "expected_value": 347425.44,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510438",
      "loan_amount": 340000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Docs",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9926,
      "expected_value": 337497.76,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510705",
      "loan_amount": 500000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 41,
      "is_locked": true,
      "ml_probability": 0.6659,
      "expected_value": 332933.05,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511192",
      "loan_amount": 328975.0,
      "product_type": "NONCONFORMING",
      "current_stage": "CTC",
      "days_at_stage": 4,
      "is_locked": true,
      "ml_probability": 0.983,
      "expected_value": 323387.51,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511171",
      "loan_amount": 371920.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 31,
      "is_locked": true,
      "ml_probability": 0.861,
      "expected_value": 320218.25,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511073",
      "loan_amount": 320000.0,
      "product_type": "CONFORMING",
      "current_stage": "CTC",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9825,
      "expected_value": 314397.32,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82507572",
      "loan_amount": 375000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Cond Review",
      "days_at_stage": 0,
      "is_locked": false,
      "ml_probability": 0.7732,
      "expected_value": 289941.28,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511003",
      "loan_amount": 295400.0,
      "product_type": "NONCONFORMING",
      "current_stage": "CTC",
      "days_at_stage": 5,
      "is_locked": true,
      "ml_probability": 0.961,
      "expected_value": 283891.95,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511228",
      "loan_amount": 279000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Fund Cond",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9814,
      "expected_value": 273808.83,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510337",
      "loan_amount": 283447.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Cond Review",
      "days_at_stage": 0,
      "is_locked": true,
      "ml_probability": 0.9455,
      "expected_value": 267985.97,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510494",
      "loan_amount": 275000.0,
      "product_type": "CONFORMING",
      "current_stage": "Docs",
      "days_at_stage": 3,
      "is_locked": true,
      "ml_probability": 0.9727,
      "expected_value": 267483.03,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "62511282",
      "loan_amount": 430000.0,
      "product_type": "2ND",
      "current_stage": "Approved",
      "days_at_stage": 23,
      "is_locked": true,
      "ml_probability": 0.6205,
      "expected_value": 266811.31,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82510511",
      "loan_amount": 333750.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Final UW",
      "days_at_stage": 0,
      "is_locked": false,
      "ml_probability": 0.7647,
      "expected_value": 255222.4,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "62510632",
      "loan_amount": 251900.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Docs",
      "days_at_stage": 3,
      "is_locked": true,
      "ml_probability": 0.9845,
      "expected_value": 247993.53,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    },
    {
      "loan_guid": "82511341",
      "loan_amount": 360000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 25,
      "is_locked": true,
      "ml_probability": 0.6647,
      "expected_value": 239301.56,
      "status": "live",
      "elimination_rule": null,
      "failure_archetype": null
    }
  ],
  "deadLoans": [
    {
      "loan_guid": "LEAD62506010",
      "loan_amount": 7100000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 174,
      "is_locked": false,
      "ml_probability": 0.0095,
      "expected_value": 67362.77,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "82509403",
      "loan_amount": 4550000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Underwriting",
      "days_at_stage": 87,
      "is_locked": false,
      "ml_probability": 0.0118,
      "expected_value": 53652.65,
      "status": "dead",
      "elimination_rule": "underwriting_unlocked_stale",
      "failure_archetype": "Stale Pre-Approval"
    },
    {
      "loan_guid": "LEAD82411000",
      "loan_amount": 3500000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 391,
      "is_locked": false,
      "ml_probability": 0.0011,
      "expected_value": 3780.86,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD92303003",
      "loan_amount": 3500000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 999,
      "is_locked": false,
      "ml_probability": 0.0013,
      "expected_value": 4630.47,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD92301190000",
      "loan_amount": 2800000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 1061,
      "is_locked": false,
      "ml_probability": 0.0013,
      "expected_value": 3704.38,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD62507003",
      "loan_amount": 2600000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 153,
      "is_locked": false,
      "ml_probability": 0.0013,
      "expected_value": 3317.03,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD92301310001",
      "loan_amount": 2520000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 1049,
      "is_locked": false,
      "ml_probability": 0.0014,
      "expected_value": 3505.77,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD82508003",
      "loan_amount": 2000000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 131,
      "is_locked": false,
      "ml_probability": 0.0014,
      "expected_value": 2814.89,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD82508002",
      "loan_amount": 2000000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 131,
      "is_locked": false,
      "ml_probability": 0.0013,
      "expected_value": 2673.15,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "82507457",
      "loan_amount": 2000000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 146,
      "is_locked": true,
      "ml_probability": 0.0166,
      "expected_value": 33269.87,
      "status": "dead",
      "elimination_rule": "approved_expired_lock",
      "failure_archetype": "Lock Expired, Gave Up"
    },
    {
      "loan_guid": "82510394",
      "loan_amount": 1642500.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Approved",
      "days_at_stage": 58,
      "is_locked": true,
      "ml_probability": 0.0118,
      "expected_value": 19410.84,
      "status": "dead",
      "elimination_rule": "approved_expired_lock",
      "failure_archetype": "Lock Expired, Gave Up"
    },
    {
      "loan_guid": "LEAD92304009",
      "loan_amount": 1350000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 972,
      "is_locked": false,
      "ml_probability": 0.0013,
      "expected_value": 1758.37,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "82509399",
      "loan_amount": 1343000.0,
      "product_type": "VA",
      "current_stage": "Underwriting",
      "days_at_stage": 88,
      "is_locked": false,
      "ml_probability": 0.0012,
      "expected_value": 1644.4,
      "status": "dead",
      "elimination_rule": "underwriting_unlocked_stale",
      "failure_archetype": "Stale Pre-Approval"
    },
    {
      "loan_guid": "LEAD62509007",
      "loan_amount": 1342000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 90,
      "is_locked": false,
      "ml_probability": 0.001,
      "expected_value": 1365.95,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD62511001",
      "loan_amount": 1200000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 40,
      "is_locked": false,
      "ml_probability": 0.0039,
      "expected_value": 4696.78,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "82510629",
      "loan_amount": 1040000.0,
      "product_type": "NONCONFORMING",
      "current_stage": "Underwriting",
      "days_at_stage": 47,
      "is_locked": false,
      "ml_probability": 0.0042,
      "expected_value": 4319.97,
      "status": "dead",
      "elimination_rule": "underwriting_unlocked_stale",
      "failure_archetype": "Stale Pre-Approval"
    },
    {
      "loan_guid": "LEAD62504014",
      "loan_amount": 1000000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 252,
      "is_locked": false,
      "ml_probability": 0.0027,
      "expected_value": 2712.02,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD82412000",
      "loan_amount": 975000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 377,
      "is_locked": false,
      "ml_probability": 0.0016,
      "expected_value": 1518.78,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "LEAD62508010",
      "loan_amount": 960000.0,
      "product_type": null,
      "current_stage": "Opened",
      "days_at_stage": 116,
      "is_locked": false,
      "ml_probability": 0.0014,
      "expected_value": 1345.95,
      "status": "dead",
      "elimination_rule": "opened_stale",
      "failure_archetype": "Opened-Only Ghost"
    },
    {
      "loan_guid": "62511008",
      "loan_amount": 806500.0,
      "product_type": "CONFORMING",
      "current_stage": "Submitted",
      "days_at_stage": 42,
      "is_locked": false,
      "ml_probability": 0.0022,
      "expected_value": 1769.45,
      "status": "dead",
      "elimination_rule": "submitted_unlocked_stale",
      "failure_archetype": "Stale Pre-Approval"
    }
  ],
  "ptChart": [
    {
      "month": "Jan \u201924",
      "rate": 30.5
    },
    {
      "month": "Feb \u201924",
      "rate": 35.4
    },
    {
      "month": "Mar \u201924",
      "rate": 37.2
    },
    {
      "month": "Apr \u201924",
      "rate": 31.7
    },
    {
      "month": "May \u201924",
      "rate": 24.0
    },
    {
      "month": "Jun \u201924",
      "rate": 20.1
    },
    {
      "month": "Jul \u201924",
      "rate": 23.6
    },
    {
      "month": "Aug \u201924",
      "rate": 25.4
    },
    {
      "month": "Sep \u201924",
      "rate": 27.6
    },
    {
      "month": "Oct \u201924",
      "rate": 32.2
    },
    {
      "month": "Nov \u201924",
      "rate": 25.7
    },
    {
      "month": "Dec \u201924",
      "rate": 24.1
    },
    {
      "month": "Jan \u201925",
      "rate": 20.0
    },
    {
      "month": "Feb \u201925",
      "rate": 20.2
    },
    {
      "month": "Mar \u201925",
      "rate": 23.9
    },
    {
      "month": "Apr \u201925",
      "rate": 24.6
    },
    {
      "month": "May \u201925",
      "rate": 23.7
    },
    {
      "month": "Jun \u201925",
      "rate": 23.5
    },
    {
      "month": "Jul \u201925",
      "rate": 25.1
    },
    {
      "month": "Aug \u201925",
      "rate": 24.0
    },
    {
      "month": "Sep \u201925",
      "rate": 28.3
    },
    {
      "month": "Oct \u201925",
      "rate": 33.4
    },
    {
      "month": "Nov \u201925",
      "rate": 32.7
    },
    {
      "month": "Dec \u201925",
      "rate": 43.5,
      "partial": true
    }
  ],
  "ptAvg": 27.5,
  "cycleBuckets": [
    {
      "range": "0\u201315 days",
      "count": 362,
      "sla": false
    },
    {
      "range": "16\u201330 days",
      "count": 2814,
      "sla": false
    },
    {
      "range": "31\u201345 days",
      "count": 1616,
      "sla": false
    },
    {
      "range": "45+ days",
      "count": 868,
      "sla": true
    }
  ],
  "cycleStats": {
    "p10": 17.0,
    "p25": 22.0,
    "median": 29.0,
    "p75": 38.0,
    "p90": 52.0,
    "mean": 33.1,
    "count": 5660,
    "above_sla": 868,
    "above_sla_pct": 15.3
  }
};

// ─── Formatting helpers ─────────────────────────────────────────────────────

const fmtM = (v) => {
  if (!v && v !== 0) return "$0";
  if (Math.abs(v) >= 1e9) return "$" + (v / 1e9).toFixed(1) + "B";
  if (Math.abs(v) >= 1e6) return "$" + (v / 1e6).toFixed(1) + "M";
  if (Math.abs(v) >= 1e3) return "$" + Math.round(v / 1e3).toLocaleString() + "K";
  return "$" + Math.round(v).toLocaleString();
};

const fmtK = (v) => {
  if (!v && v !== 0) return "$0";
  if (Math.abs(v) >= 1e6) return "$" + (v / 1e6).toFixed(2) + "M";
  if (Math.abs(v) >= 1e3) return "$" + Math.round(v / 1e3).toLocaleString() + "K";
  return "$" + Math.round(v).toLocaleString();
};

const probColor = (v) =>
  v > 0.7 ? "#3DAA7F" : v > 0.4 ? "#E8913A" : "#E85A5A";

const RULE_LABELS = {
  opened_stale: "Stale at Open (30+ days)",
  application_stale: "Stale at App (30+ days)",
  submitted_unlocked_stale: "Submitted, No Lock (22+ days)",
  underwriting_unlocked_stale: "UW, No Lock (22+ days)",
  approved_expired_lock: "Lock Expired at Approved",
};

// ─── StatCard ───────────────────────────────────────────────────────────────

function StatCard({ title, value, subtitle, color }) {
  return (
    <div
      className="bg-white rounded-lg shadow-sm"
      style={{ padding: 24, border: "1px solid #E5E7EB" }}
    >
      <p
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: "#9CA3AF",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          margin: 0,
        }}
      >
        {title}
      </p>
      <p
        style={{
          fontSize: 28,
          fontWeight: 700,
          color: color || "#1A2332",
          margin: "8px 0 0",
          letterSpacing: "-0.02em",
        }}
      >
        {value}
      </p>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 0" }}>
        {subtitle}
      </p>
    </div>
  );
}

// ─── Probability bar ────────────────────────────────────────────────────────

function ProbBar({ value }) {
  const pct = Math.round(value * 100);
  const color = probColor(value);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 100 }}>
      <div
        style={{
          width: 52,
          height: 6,
          borderRadius: 3,
          background: "#E5E7EB",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: pct + "%",
            height: "100%",
            borderRadius: 3,
            background: color,
          }}
        />
      </div>
      <span
        style={{
          fontSize: 12,
          fontWeight: 600,
          color,
          fontVariantNumeric: "tabular-nums",
          minWidth: 32,
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

// ─── Tooltip ────────────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label, suffix }) {
  if (!active || !payload || !payload.length) return null;
  const v = payload[0].value;
  const display = typeof v === "number" ? v.toLocaleString() : v;
  return (
    <div
      style={{
        background: "white",
        padding: "8px 14px",
        borderRadius: 8,
        boxShadow: "0 4px 12px rgba(0,0,0,0.10)",
        border: "1px solid #E5E7EB",
        fontSize: 13,
      }}
    >
      <div style={{ fontWeight: 600, color: "#374151" }}>{label}</div>
      <div style={{ color: payload[0].stroke || payload[0].fill || "#4A90D9", marginTop: 2 }}>
        {display}
        {suffix || ""}
      </div>
    </div>
  );
}

// ─── Loan Priority Table ────────────────────────────────────────────────────

function LoanTable() {
  const [tab, setTab] = useState("live");
  const [expanded, setExpanded] = useState(false);
  const VISIBLE_ROWS = 15;
  const allLoans = tab === "live" ? DATA.liveLoans : DATA.deadLoans;
  const loans = expanded ? allLoans : allLoans.slice(0, VISIBLE_ROWS);
  const hasMore = allLoans.length > VISIBLE_ROWS;
  const isDead = tab === "dead";

  const tabStyle = (key, activeColor) => ({
    padding: "14px 24px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    background: "transparent",
    border: "none",
    borderBottom: tab === key ? "2.5px solid " + activeColor : "2.5px solid transparent",
    color: tab === key ? activeColor : "#9CA3AF",
    transition: "all 0.15s ease",
  });

  const th = (label, extra) => (
    <th
      style={{
        padding: "11px 16px",
        fontSize: 10,
        fontWeight: 700,
        color: "#9CA3AF",
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        whiteSpace: "nowrap",
        ...extra,
      }}
    >
      {label}
    </th>
  );

  return (
    <div
      className="bg-white rounded-lg shadow-sm"
      style={{ border: "1px solid #E5E7EB", overflow: "hidden" }}
    >
      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #E5E7EB" }}>
        <button style={tabStyle("live", "#E8913A")} onClick={() => { setTab("live"); setExpanded(false); }}>
          Live Pipeline ({DATA.liveLoans.length})
        </button>
        <button style={tabStyle("dead", "#E85A5A")} onClick={() => { setTab("dead"); setExpanded(false); }}>
          Eliminated ({DATA.deadLoans.length})
        </button>
      </div>

      {/* Callout */}
      <div
        style={{
          padding: "10px 24px",
          fontSize: 13,
          lineHeight: 1.5,
          background: isDead ? "#FEF2F2" : "#EFF6FF",
          color: isDead ? "#991B1B" : "#1E40AF",
          borderBottom: "1px solid " + (isDead ? "#FECACA" : "#DBEAFE"),
        }}
      >
        {isDead
          ? "These loans match historical dead-loan patterns (<2% funding rate). Removing them sharpens projections."
          : "Ranked by expected value \u2014 probability \u00d7 loan amount. Focus your team\u2019s effort top-down."}
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#F9FAFB", textAlign: "left" }}>
              {th("#", { width: 48 })}
              {th("Product")}
              {th("Stage")}
              {th("Days", { textAlign: "right" })}
              {th("Lock", { textAlign: "center" })}
              {th("Probability")}
              {th("Amount", { textAlign: "right" })}
              {th("Exp. Value", { textAlign: "right" })}
              {isDead && th("Elimination Rule")}
              {isDead && th("Archetype")}
            </tr>
          </thead>
          <tbody>
            {loans.map((loan, i) => (
              <tr
                key={loan.loan_guid}
                style={{
                  borderTop: "1px solid #F3F4F6",
                  background: isDead
                    ? "rgba(254,242,242,0.25)"
                    : i % 2 === 1
                    ? "#FAFBFC"
                    : "white",
                  opacity: isDead ? 0.72 : 1,
                  fontSize: 13,
                }}
              >
                <td style={{ padding: "10px 16px", color: "#D1D5DB", fontWeight: 600 }}>
                  {i + 1}
                </td>
                <td
                  style={{
                    padding: "10px 16px",
                    fontWeight: 600,
                    color: isDead ? "#9CA3AF" : "#1A2332",
                  }}
                >
                  {loan.product_type || "\u2014"}
                </td>
                <td style={{ padding: "10px 16px", color: "#4B5563" }}>
                  {loan.current_stage}
                </td>
                <td
                  style={{
                    padding: "10px 16px",
                    textAlign: "right",
                    fontVariantNumeric: "tabular-nums",
                    color: "#4B5563",
                  }}
                >
                  {loan.days_at_stage}d
                </td>
                <td style={{ padding: "10px 16px", textAlign: "center", fontSize: 15 }}>
                  {loan.is_locked ? "\ud83d\udd12" : "\ud83d\udd13"}
                </td>
                <td style={{ padding: "10px 16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <ProbBar value={loan.ml_probability} />
                    {!isDead && loan.ml_probability < 0.25 && (
                      <span title="Low probability, high expected value" style={{ color: "#E8913A", fontSize: 14, lineHeight: 1, cursor: "help" }}>{"\u26a0"}</span>
                    )}
                  </div>
                </td>
                <td
                  style={{
                    padding: "10px 16px",
                    textAlign: "right",
                    fontFamily: "ui-monospace, monospace",
                    fontSize: 12,
                    fontVariantNumeric: "tabular-nums",
                    color: "#4B5563",
                  }}
                >
                  {fmtK(loan.loan_amount)}
                </td>
                <td
                  style={{
                    padding: "10px 16px",
                    textAlign: "right",
                    fontFamily: "ui-monospace, monospace",
                    fontSize: 12,
                    fontWeight: 700,
                    fontVariantNumeric: "tabular-nums",
                    color: isDead ? "#9CA3AF" : "#1A2332",
                  }}
                >
                  {fmtK(loan.expected_value)}
                </td>
                {isDead && (
                  <td style={{ padding: "10px 16px", fontSize: 11, color: "#6B7280" }}>
                    {RULE_LABELS[loan.elimination_rule] || loan.elimination_rule || "\u2014"}
                  </td>
                )}
                {isDead && (
                  <td style={{ padding: "10px 16px", fontSize: 11, color: "#6B7280" }}>
                    {loan.failure_archetype || "\u2014"}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Show all / collapse toggle */}
      {hasMore && (
        <div style={{ textAlign: "center", padding: "12px 0", borderTop: "1px solid #F3F4F6" }}>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              background: "none",
              border: "1px solid #D1D5DB",
              borderRadius: 6,
              padding: "6px 20px",
              fontSize: 12,
              fontWeight: 600,
              color: "#6B7280",
              cursor: "pointer",
            }}
          >
            {expanded ? "Collapse" : "Show all " + allLoans.length + " loans"}
          </button>
        </div>
      )}

      {/* Low-probability footnote (live tab only) */}
      {!isDead && allLoans.some((l) => l.ml_probability < 0.25) && (
        <div style={{ padding: "8px 24px 12px", fontSize: 11, color: "#9CA3AF" }}>
          {"\u26a0"} Low-probability, high-value loans &mdash; consider whether ops effort is justified despite large expected value.
        </div>
      )}
    </div>
  );
}

// ─── Pull-Through Chart ─────────────────────────────────────────────────────

function PTDot(props) {
  const { cx, cy, index, payload } = props;
  if (!cx || !cy) return null;
  if (payload && payload.partial) {
    // Hollow dashed circle for partial month
    return (
      <g>
        <circle cx={cx} cy={cy} r={5} fill="white" stroke="#4A90D9" strokeWidth={2} strokeDasharray="3 2" />
        <text x={cx + 10} y={cy - 8} fontSize={9} fill="#9CA3AF" fontStyle="italic">Partial month</text>
      </g>
    );
  }
  return <circle cx={cx} cy={cy} r={2.5} fill="#4A90D9" strokeWidth={0} />;
}

function PullThroughChart() {
  return (
    <div
      className="bg-white rounded-lg shadow-sm"
      style={{ padding: 24, border: "1px solid #E5E7EB" }}
    >
      <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1A2332", margin: 0 }}>
        Pull-Through Rate \u2014 Monthly Trend
      </h3>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 0" }}>
        Funded loans as % of active pipeline at month start
      </p>
      <div style={{ height: 280, marginTop: 20 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={DATA.ptChart} margin={{ top: 8, right: 60, bottom: 30, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 10, fill: "#9CA3AF" }}
              interval={2}
              angle={-40}
              textAnchor="end"
              height={55}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => v + "%"}
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
              domain={[0, "dataMax + 5"]}
              width={48}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<ChartTooltip suffix="%" />} />
            <ReferenceLine
              y={DATA.ptAvg}
              stroke="#D1D5DB"
              strokeDasharray="6 3"
              label={{
                value: "Avg " + DATA.ptAvg + "%",
                fill: "#9CA3AF",
                fontSize: 10,
                position: "insideTopRight",
              }}
            />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="#4A90D9"
              strokeWidth={2.5}
              dot={<PTDot />}
              activeDot={{ r: 5, stroke: "#4A90D9", strokeWidth: 2, fill: "white" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Cycle Time Chart ───────────────────────────────────────────────────────

function CycleTimeChart() {
  const cs = DATA.cycleStats;
  return (
    <div
      className="bg-white rounded-lg shadow-sm"
      style={{ padding: 24, border: "1px solid #E5E7EB" }}
    >
      <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1A2332", margin: 0 }}>
        Application to Funding \u2014 Cycle Times
      </h3>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 0" }}>
        <span style={{ color: "#E85A5A", fontWeight: 600 }}>{cs.above_sla_pct}%</span> of
        loans exceed 45-day SLA
      </p>
      <div style={{ height: 260, marginTop: 20 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={DATA.cycleBuckets}
            margin={{ top: 8, right: 16, bottom: 5, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
            <XAxis
              dataKey="range"
              tick={{ fontSize: 12, fill: "#6B7280" }}
              tickLine={false}
              axisLine={{ stroke: "#E5E7EB" }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
              width={50}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => v.toLocaleString()}
            />
            <Tooltip content={<ChartTooltip suffix=" loans" />} />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={90}>
              {DATA.cycleBuckets.map((entry, i) => (
                <Cell key={i} fill={entry.sla ? "#E85A5A" : "#4A90D9"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          marginTop: 14,
          fontSize: 11,
          color: "#9CA3AF",
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: 4,
            background: "#4A90D9",
            marginRight: 6,
          }}
        />
        Within SLA
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: 4,
            background: "#E85A5A",
            marginLeft: 20,
            marginRight: 6,
          }}
        />
        SLA Breach
        <span
          style={{
            marginLeft: "auto",
            display: "flex",
            gap: 20,
            fontWeight: 600,
            color: "#6B7280",
          }}
        >
          <span>Median: {cs.median}d</span>
          <span>P75: {cs.p75}d</span>
          <span>P90: {cs.p90}d</span>
        </span>
      </div>
    </div>
  );
}

// ─── Main Dashboard ─────────────────────────────────────────────────────────

export default function FlexPointDashboard() {
  const s = DATA.summary;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#F5F6F8",
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
      }}
    >
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header
        style={{
          background: "#1A2332",
          padding: "20px 32px",
          boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
        }}
      >
        <div
          style={{
            maxWidth: 1400,
            margin: "0 auto",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <h1
              style={{
                fontSize: 21,
                fontWeight: 700,
                color: "white",
                margin: 0,
                letterSpacing: "-0.01em",
              }}
            >
              FlexPoint Funding Forecast
            </h1>
            <p style={{ fontSize: 13, color: "#8B95A5", margin: "3px 0 0" }}>
              Pipeline Intelligence &mdash; Gallus Insights
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <p style={{ fontSize: 14, color: "#E5E7EB", fontWeight: 600, margin: 0 }}>
              December 2025
            </p>
            <p style={{ fontSize: 11, color: "#6B7280", margin: "3px 0 0" }}>
              Snapshot: {s.snapshot_date} &middot; Model: {s.model_used}
            </p>
          </div>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "28px 32px 16px" }}>
        {/* Summary cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 24,
          }}
        >
          <StatCard
            title="Total Pipeline"
            value={fmtM(s.total_pipeline_value)}
            subtitle={s.total_pipeline_loans.toLocaleString() + " active loans"}
          />
          <StatCard
            title="Live Pipeline"
            value={fmtM(s.live_pipeline_value)}
            subtitle={s.live_pipeline_loans.toLocaleString() + " loans passing filter"}
            color="#3DAA7F"
          />
          <StatCard
            title="Eliminated"
            value={fmtM(s.dead_pipeline_value)}
            subtitle={s.elimination_stats.pct_eliminated + "% of pipeline"}
            color="#E85A5A"
          />
          <StatCard
            title="Projected Funding"
            value={fmtM(s.projected_total)}
            subtitle={"Dec 2025 \u2014 " + fmtM(s.already_funded_value) + " already funded"}
            color="#E8913A"
          />
        </div>

        {/* Unit economics callout */}
        <div
          style={{
            marginTop: 24,
            background: "#1A2332",
            borderRadius: 8,
            padding: "14px 24px",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <span style={{ fontSize: 18 }}>&#x1F4C8;</span>
          <p style={{ margin: 0, fontSize: 13, color: "#E5E7EB", lineHeight: 1.5 }}>
            If prioritization improves pull-through by <span style={{ color: "#E8913A", fontWeight: 700 }}>1%</span>, that&rsquo;s
            ~<span style={{ color: "#3DAA7F", fontWeight: 700 }}>$400K additional revenue</span> per $1B funded volume.
          </p>
        </div>

        {/* Loan table */}
        <div style={{ marginTop: 24 }}>
          <LoanTable />
        </div>

        {/* Charts */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 24,
            marginTop: 32,
          }}
        >
          <PullThroughChart />
          <CycleTimeChart />
        </div>

        {/* Footer */}
        <div
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "#9CA3AF",
            padding: "28px 0 12px",
          }}
        >
          FlexPoint Funding Forecast &middot; Data as of {s.snapshot_date} &middot;{" "}
          {(s.overall_pull_through * 100).toFixed(1)}% historical pull-through &middot;
          Median cycle: {s.median_cycle_days} days
        </div>
      </div>
    </div>
  );
}
