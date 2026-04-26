#!/usr/bin/env python3
"""
Build the Week 4 speaker script PDF for the Augie call.
Split between Ajer and Liam.
"""
from fpdf import FPDF
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "week4" / "week4_speaker_script.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)


class ScriptPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(160, 160, 160)
        self.cell(0, 8, "FlexPoint Funding Forecast -- Week 4 Demo Script", align="R")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(180, 180, 180)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_header(self, text):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(26, 35, 50)
        self.cell(0, 10, text)
        self.ln(8)
        # Copper underline
        self.set_draw_color(212, 149, 106)
        self.set_line_width(0.6)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(6)

    def speaker(self, name):
        self.ln(3)
        if name == "AJER":
            self.set_fill_color(212, 149, 106)
            self.set_text_color(255, 255, 255)
        else:
            self.set_fill_color(106, 163, 212)
            self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        self.cell(22, 6, f"  {name}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(40, 40, 40)

    def talk(self, text):
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def stage_direction(self, text):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(140, 140, 140)
        self.multi_cell(0, 5, f"[{text}]")
        self.ln(1)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        x = self.get_x()
        self.cell(6, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(0.5)


pdf = ScriptPDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# ─── Title Page ──────────────────────────────────────────────────────────────

pdf.ln(30)
pdf.set_font("Helvetica", "B", 28)
pdf.set_text_color(26, 35, 50)
pdf.cell(0, 14, "FlexPoint Funding Forecast", align="C")
pdf.ln(12)
pdf.set_font("Helvetica", "", 14)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 8, "Week 4 Demo Walkthrough", align="C")
pdf.ln(6)
pdf.cell(0, 8, "Speaker Script for Augie Call", align="C")
pdf.ln(20)

# Copper line
pdf.set_draw_color(212, 149, 106)
pdf.set_line_width(0.8)
pdf.line(60, pdf.get_y(), 150, pdf.get_y())
pdf.ln(16)

pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 7, "Presenters:  Ajer  |  Liam", align="C")
pdf.ln(6)
pdf.cell(0, 7, "Audience:  Augie, Mariana, Israel", align="C")
pdf.ln(6)
pdf.cell(0, 7, "Duration:  ~15-20 minutes", align="C")
pdf.ln(6)
pdf.cell(0, 7, "Format:  Live dashboard demo + discussion", align="C")

pdf.ln(20)
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(26, 35, 50)
pdf.cell(0, 7, "Speaker Key:", align="L")
pdf.ln(6)
pdf.set_font("Helvetica", "", 10)

pdf.set_fill_color(212, 149, 106)
pdf.set_text_color(255, 255, 255)
pdf.cell(22, 6, "  AJER", fill=True)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 6, "   Model architecture, data, accuracy, technical details")
pdf.ln(8)
pdf.set_fill_color(106, 163, 212)
pdf.set_text_color(255, 255, 255)
pdf.cell(22, 6, "  LIAM", fill=True)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 6, "   Dashboard features, client value, ops workflow, business impact")
pdf.ln(4)


# ─── Section 1: Opening ─────────────────────────────────────────────────────

pdf.add_page()
pdf.section_header("1. OPENING  (1 min)")

pdf.speaker("LIAM")
pdf.talk(
    "Thanks for jumping on, Augie. Today we're going to walk you through the "
    "pipeline intelligence dashboard we've built on top of the forecasting model. "
    "The goal here is to show you what this looks like as a product you could "
    "offer your clients -- not just the model accuracy, but the actual interface "
    "an ops manager would use day to day."
)

pdf.speaker("AJER")
pdf.talk(
    "Quick recap of where we are: over the past four weeks we've gone from a raw "
    "dataset of 15,000 loans to a trained ML model that predicts monthly funding "
    "volume within about 6% accuracy at mid-month. Today we're showing the "
    "dashboard that makes that model usable."
)

pdf.speaker("LIAM")
pdf.talk(
    "The dashboard has three tabs -- Overview, Watch List, and Trends. We'll walk "
    "through each one. Ajer will cover the model and data side, I'll cover the "
    "client-facing features and how an ops team would actually use this."
)

pdf.stage_direction("Open the dashboard -- Overview tab should be visible")


# ─── Section 2: Overview Tab ────────────────────────────────────────────────

pdf.add_page()
pdf.section_header("2. OVERVIEW TAB -- The Executive Summary  (4 min)")

pdf.stage_direction("Point to the five stat cards at the top")

pdf.speaker("LIAM")
pdf.talk(
    "This is the first thing a client sees when they open the dashboard. Five "
    "numbers that tell the full story at a glance:"
)
pdf.bullet("Total Pipeline: $314M across 1,109 loans currently in the system")
pdf.bullet("Live Pipeline: $147M across 708 loans that our model considers viable")
pdf.bullet(
    "Eliminated: $167M flagged as effectively dead -- 36% of the pipeline. "
    "These are loans that match historical patterns where less than 2% ever fund."
)
pdf.bullet(
    "Projected Funding: $100.6M for December. That's the model's prediction of "
    "what will actually fund by month end, based on the current pipeline state."
)
pdf.bullet(
    "Model Accuracy: 5.8% MAPE -- meaning on average our mid-month prediction "
    "is within 5.8% of what actually happens. 19 out of 24 test months were "
    "within 10% accuracy."
)

pdf.speaker("AJER")
pdf.talk(
    "To explain how we get that $100.6M number -- the model scores every single "
    "loan in the pipeline with a probability of funding by month end. A loan at "
    "Clear to Close with a rate lock has maybe a 95% probability. A loan sitting "
    "at Approved for 45 days without a lock might be 8%. We multiply each "
    "probability by the loan amount and sum it all up. That's the projection."
)
pdf.talk(
    "The model is a Gradient Boosting classifier trained on two years of historical "
    "pipeline snapshots -- about 80,000 loan-month observations. It uses 27 features "
    "including pipeline stage, days at stage, rate lock status, product type, and "
    "loan characteristics. We retrain on a rolling 12-month window so it adapts "
    "to market changes."
)

pdf.stage_direction("Scroll down to the Pipeline Stage Distribution chart")

pdf.speaker("LIAM")
pdf.talk(
    "This funnel shows where every loan sits in the pipeline right now. The gray "
    "bars are total loans including eliminated ones, and the blue bars are the "
    "live pipeline."
)
pdf.talk(
    "You can see immediately that Approved is the bottleneck -- 468 loans sitting "
    "there. That's where the most uncertainty is. Once loans get past Approved into "
    "Condition Review, Clear to Close, and beyond, the funding probability jumps "
    "above 90%. The modeling value is really in that middle zone -- Submitted "
    "through CTC -- where the model differentiates which loans will make it."
)

pdf.stage_direction("Point to the Channel Breakdown and Product Breakdown side by side")

pdf.speaker("LIAM")
pdf.talk(
    "Channel breakdown shows Wholesale versus Retail. Wholesale dominates -- 649 "
    "loans, $31.8M projected, 30% average probability. Retail is 59 loans with "
    "only $670K projected and a 5% average probability. That's a 6x difference "
    "in pull-through rate. A client would want to know that -- it tells them where "
    "their operations effort is actually paying off."
)
pdf.talk(
    "Product breakdown shows the same story by loan type. Nonconforming leads at "
    "$23M projected. FHA and Second liens follow. This helps the client understand "
    "not just how much will fund, but the composition of that funding."
)


# ─── Section 3: Watch List Tab ──────────────────────────────────────────────

pdf.add_page()
pdf.section_header("3. WATCH LIST TAB -- Ops Action Center  (5 min)")

pdf.stage_direction("Click the Watch List tab")

pdf.speaker("LIAM")
pdf.talk(
    "This is where the dashboard goes from informational to actionable. The Watch "
    "List tab has two sections: the At-Risk Watch List at the top, and the full "
    "Loan Priority Table below it."
)

pdf.speaker("LIAM")
pdf.talk(
    "The At-Risk Watch List flags 59 loans that need immediate ops attention. "
    "These aren't the dead loans -- those are already eliminated. These are live "
    "loans that could still fund but have warning signs. Each loan gets a specific "
    "reason label explaining exactly what's wrong."
)

pdf.talk("The risk flags fall into four categories:")
pdf.bullet(
    "\"Rate lock expires within 7 days -- still at Cond Review\" -- these are "
    "urgent. The lock is about to die and the loan hasn't cleared to close yet. "
    "The ops team needs to either push the loan through or extend the lock."
)
pdf.bullet(
    "\"No rate lock -- 3% funding probability\" -- high-value loans sitting in "
    "the pipeline without a rate lock. The model gives them very low odds. "
    "The question for the client is: is it worth the effort to pursue these?"
)
pdf.bullet(
    "\"No rate lock despite reaching CTC\" -- unusual. A loan made it to Clear "
    "to Close without ever locking a rate. Something is off."
)
pdf.bullet(
    "\"Sitting at Approved for 151 days\" -- a loan that's been stuck for five "
    "months. Either it needs to be actively worked or written off."
)

pdf.speaker("AJER")
pdf.talk(
    "The key design choice here is that each risk reason is specific to the loan -- "
    "it includes the actual stage, the actual number of days, the actual probability. "
    "It's not a generic \"at risk\" label. An ops manager can read the badge and "
    "know exactly what to do without clicking into anything."
)

pdf.stage_direction("Scroll down to the Loan Priority Table")

pdf.speaker("LIAM")
pdf.talk(
    "Below the watch list is the full loan priority table. This has two tabs -- "
    "Live Pipeline and Eliminated."
)
pdf.talk(
    "Live Pipeline ranks every loan by expected value -- that's probability times "
    "loan amount. The loan at the top is a $2.1M Nonconforming loan at Condition "
    "Review with a 92% probability -- $1.9M expected value. The idea is simple: "
    "work the list top to bottom, and you're maximizing the dollar impact of your "
    "team's time."
)
pdf.talk(
    "The Eliminated tab shows the loans the model flagged as dead. Each one has "
    "a rule explaining why -- \"Stale at Open 30+ days,\" \"Lock Expired at "
    "Approved,\" and so on. These rules are based on historical data: across "
    "16,000+ observations, loans matching these patterns funded less than 0.1% "
    "of the time. So we remove them from the projection to keep it accurate."
)


# ─── Section 4: Trends Tab ──────────────────────────────────────────────────

pdf.add_page()
pdf.section_header("4. TRENDS TAB -- Historical Context  (2 min)")

pdf.stage_direction("Click the Trends tab")

pdf.speaker("AJER")
pdf.talk(
    "The Trends tab gives historical context. Two charts: pull-through rate over "
    "time and cycle time distribution."
)
pdf.talk(
    "Pull-through rate shows what percentage of the pipeline actually funded each "
    "month from January 2024 through December 2025. The average is 27.5%. You "
    "can see it fluctuates -- peaks around 35% in early 2024, dips to 20% in "
    "early 2025, and trends back up recently. This context helps a client "
    "understand whether their current month is normal or an outlier."
)

pdf.speaker("LIAM")
pdf.talk(
    "The cycle time chart shows how long loans take from application to funding. "
    "The median is 29 days. Most loans fund in the 16-30 day window. But 15.3% "
    "exceed the 45-day SLA -- that's the red bar. Those are the loans where "
    "something went wrong in the process."
)
pdf.talk(
    "For a client, this answers the question: \"How long should I expect a loan "
    "to take?\" And more importantly: \"How many of my loans are taking too long?\""
)


# ─── Section 5: Model Deep Dive ─────────────────────────────────────────────

pdf.add_page()
pdf.section_header("5. MODEL DEEP DIVE -- For Augie  (3 min)")

pdf.speaker("AJER")
pdf.talk(
    "Augie, you asked us to build something that uses pipeline stage as the "
    "foundation, stratified by product type and loan purpose, with time-at-stage "
    "as a key factor. That's exactly what we did."
)
pdf.talk("Here's how the model works under the hood:")
pdf.bullet(
    "Step 1: Pipeline Reconstruction -- for any given date, we rebuild the state "
    "of the pipeline. Which loans were open, what stage they were at, how long "
    "they'd been there. This uses the 13 milestone date columns in the data."
)
pdf.bullet(
    "Step 2: Transition Tables -- we compute historical probabilities. \"Of all "
    "loans that were at Approved on day 15 of a month, what fraction actually "
    "funded by month end?\" We stratify by product type and loan purpose, with "
    "smoothing for small sample sizes."
)
pdf.bullet(
    "Step 3: ML Layer -- a Gradient Boosting model refines the base probabilities "
    "using 27 features. The top feature is rate lock expiry vs month end -- it "
    "explains 68% of the model's decisions. Days at stage and the transition "
    "table probability are second and third."
)
pdf.bullet(
    "Step 4: Aggregation -- multiply each loan's probability by its amount, sum "
    "it up, add what's already funded, and that's the projection."
)

pdf.speaker("AJER")
pdf.talk(
    "On accuracy: we backtested across 24 months, January 2024 through December "
    "2025. At mid-month, the model achieves 5.8% MAPE on a rolling retrain "
    "basis. 19 of 24 months were within 10% error. The worst month was November "
    "2025 at 13% -- still within a reasonable range."
)
pdf.talk(
    "You told us to build 3-5 models and compare. We trained Logistic Regression, "
    "Gradient Boosting, Random Forest, and LightGBM. Gradient Boosting won on "
    "calibration -- which is the metric that matters most when you're summing "
    "probabilities across hundreds of loans."
)


# ─── Section 6: Client Value Proposition ─────────────────────────────────────

pdf.add_page()
pdf.section_header("6. CLIENT VALUE PROPOSITION  (3 min)")

pdf.speaker("LIAM")
pdf.talk(
    "So Augie, stepping back -- here's what this looks like as a product offering "
    "for your clients:"
)

pdf.ln(2)
pdf.set_font("Helvetica", "B", 11)
pdf.set_text_color(26, 35, 50)
pdf.cell(0, 7, "What the client gets:")
pdf.ln(7)
pdf.set_font("Helvetica", "", 10.5)
pdf.set_text_color(40, 40, 40)

pdf.bullet(
    "Daily funding projections -- not a guess, not a gut feel, but a model-backed "
    "number they can plan around. Warehouse line management, staffing, cash flow "
    "forecasting -- all improved."
)
pdf.bullet(
    "Pipeline intelligence -- knowing which loans to prioritize, which are dead "
    "weight, and which need urgent attention. The watch list alone could save "
    "an ops team hours per week of chasing dead leads."
)
pdf.bullet(
    "Historical benchmarking -- understanding pull-through rates by product and "
    "channel, cycle time distributions, and how the current month compares "
    "to historical norms."
)
pdf.bullet(
    "Elimination filtering -- automatically identifying the 36% of pipeline that "
    "historically never funds. Removing that noise makes every other metric "
    "more accurate and more useful."
)

pdf.ln(2)
pdf.set_font("Helvetica", "B", 11)
pdf.set_text_color(26, 35, 50)
pdf.cell(0, 7, "The unit economics:")
pdf.ln(7)
pdf.set_font("Helvetica", "", 10.5)
pdf.set_text_color(40, 40, 40)

pdf.talk(
    "If this dashboard helps a client improve their pull-through rate by just 1% "
    "-- going from 39% to 40% -- that translates to roughly $400K in additional "
    "revenue per billion dollars of funded volume. For a lender doing $100M+ per "
    "month, that's real money. And we think the combination of prioritization, "
    "early warning, and dead loan removal can deliver more than 1%."
)

# ─── Section 7: Closing / Next Steps ────────────────────────────────────────

pdf.add_page()
pdf.section_header("7. NEXT STEPS & DISCUSSION  (2 min)")

pdf.speaker("AJER")
pdf.talk(
    "In terms of what's next technically, there are a few directions we could go:"
)
pdf.bullet(
    "Real-time integration -- right now this runs on a snapshot. We could wire it "
    "to pull from the LOS daily and update automatically."
)
pdf.bullet(
    "Survival model -- we built four model types but haven't implemented a survival/"
    "hazard model yet. That could improve the time-at-stage predictions."
)
pdf.bullet(
    "Scenario analysis -- \"What if we push these 10 loans from Approved to CTC "
    "this week?\" The model can answer that."
)

pdf.speaker("LIAM")
pdf.talk(
    "From the product side:"
)
pdf.bullet(
    "Client onboarding flow -- how does a new lender plug their data into this?"
)
pdf.bullet(
    "Alerting -- push notifications when high-value loans hit risk thresholds"
)
pdf.bullet(
    "Multi-month view -- show projected funding for the next 2-3 months, "
    "not just the current month"
)

pdf.speaker("LIAM")
pdf.talk(
    "Augie, we'd love your feedback on two things: first, does this match what "
    "you'd want to put in front of a client? And second, what would you change "
    "or add to make it more compelling?"
)

pdf.stage_direction("Open for discussion")


# ─── Write ───────────────────────────────────────────────────────────────────

pdf.output(str(OUT))
print(f"Written: {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")
