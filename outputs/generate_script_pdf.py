#!/usr/bin/env python3
"""Generate the Dashboard v2 Walkthrough speaker script PDF — verbatim read-off script."""

from fpdf import FPDF
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "dashboardv2_script.pdf")


class ScriptPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=22)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-18)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"Page {self.page_no() - 1}", align="C")

    def add_cover_page(self):
        self.add_page()
        self.ln(55)
        self.set_font("Helvetica", "B", 30)
        self.set_text_color(20, 50, 90)
        self.cell(0, 14, "FlexPoint Pipeline Intelligence", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("Helvetica", "", 22)
        self.set_text_color(60, 60, 60)
        self.cell(0, 12, "Dashboard v2 Walkthrough", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_draw_color(20, 50, 90)
        self.set_line_width(0.8)
        self.line(60, self.get_y(), self.w - 60, self.get_y())
        self.ln(10)
        self.set_font("Helvetica", "", 13)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "Speaker Script  |  April 2025", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(16)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(20, 50, 90)
        self.cell(0, 8, "ATTENDEES", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 7, "Augie  |  Mariana  |  Israel", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(20, 50, 90)
        self.cell(0, 8, "SPEAKERS", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 7, "Liam (Project Lead)  |  Ajer (Dashboard & Analytics)", align="C", new_x="LMARGIN", new_y="NEXT")

    def section_header(self, title):
        self.ln(6)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(20, 50, 90)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(20, 50, 90)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)

    def speaker(self, name):
        self.set_font("Helvetica", "B", 11)
        if name == "LIAM":
            self.set_text_color(140, 40, 40)
        else:
            self.set_text_color(40, 100, 60)
        self.cell(0, 7, f"{name}:", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def say(self, text):
        """Main script text — what to actually say."""
        self.set_font("Helvetica", "", 11)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 6.5, text)
        self.ln(3)

    def action(self, text):
        """Stage direction — what to do on screen."""
        self.set_font("Helvetica", "I", 9.5)
        self.set_text_color(20, 50, 90)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 5.5, f"[{text}]")
        self.ln(2)

    def note(self, text):
        """Internal speaker note in a shaded box."""
        x = self.l_margin
        inner_w = self.w - self.l_margin - self.r_margin
        pad = 5
        line_h = 5
        self.set_font("Helvetica", "I", 9)
        lines = self.multi_cell(inner_w - 2 * pad, line_h, text, dry_run=True, output="LINES")
        box_h = len(lines) * line_h + 2 * pad

        if self.get_y() + box_h + 4 > self.h - self.b_margin:
            self.add_page()

        y_start = self.get_y()
        self.set_fill_color(242, 238, 230)
        self.set_draw_color(210, 195, 170)
        self.set_line_width(0.3)
        self.rect(x, y_start, inner_w, box_h, style="DF")
        self.set_xy(x + pad, y_start + pad)
        self.set_text_color(90, 75, 50)
        self.multi_cell(inner_w - 2 * pad, line_h, text)
        self.set_y(y_start + box_h + 4)


def build_pdf():
    pdf = ScriptPDF()
    pdf.set_left_margin(22)
    pdf.set_right_margin(22)

    # ── COVER ──
    pdf.add_cover_page()

    # ══════════════════════════════════════════════════════════
    # 1. OPENING
    # ══════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_header("1. OPENING")
    pdf.speaker("LIAM")

    pdf.say(
        "Hey Augie, Mariana, Israel -- thanks for jumping on. Today we want to walk you "
        "through the upgraded dashboard. Quick recap on the model, then we'll spend most "
        "of the time on 6 new analytics features we've added."
    )
    pdf.say(
        "So as a refresher, the model scores every active loan in your pipeline by its "
        "probability of funding this month. It looks at the loan's current stage, product "
        "type, purpose, how long it's been sitting at that stage, rate lock status, and "
        "about 20 other features. Then it sums up probability times loan amount across "
        "the whole pipeline to get a dollar projection."
    )
    pdf.say(
        "On accuracy -- we backtested across 24 months, January 2024 through December 2025. "
        "The average error is 5.8%. 19 of those 24 months, the prediction landed within 10% "
        "of actual funded volume. October 2025 we were off by less than a tenth of a percent."
    )
    pdf.say(
        "The foundation is solid. What we've done now is build a set of features on top of "
        "that model that go beyond just predicting -- they tell you where the problems are "
        "and what to do about them. Ajer is going to walk you through most of these, but let "
        "me start with the overview."
    )

    # ══════════════════════════════════════════════════════════
    # 2. DASHBOARD OVERVIEW
    # ══════════════════════════════════════════════════════════
    pdf.section_header("2. DASHBOARD OVERVIEW")
    pdf.speaker("LIAM")
    pdf.action("Open the dashboard. You're on the Overview tab.")

    pdf.say(
        "First thing you'll notice at the top is a section called This Week's Top Actions. "
        "These are 6 specific, ranked recommendations with dollar estimates. We'll come back "
        "to that -- it's the punchline."
    )
    pdf.say(
        "The KPI row below shows the full picture. Total pipeline is $314 million across "
        "about 1,100 loans. After the elimination filter removes dead loans -- ones matching "
        "historical patterns with under 2% funding rate -- we're left with $147 million in "
        "live pipeline from 708 loans. The model projects $100.6 million will actually fund "
        "this month, and $68 million of that has already funded."
    )
    pdf.say(
        "The model accuracy card on the right shows 5.8% MAPE, 19 out of 24 months within "
        "10%. That's the credibility anchor for everything else we're about to show."
    )
    pdf.action("Point briefly at the stage funnel chart.")
    pdf.say(
        "The stage funnel below shows where loans sit in the pipeline. You can already see "
        "that the Approved stage has the most loans by far -- 468. That's the bottleneck, "
        "and we'll show you exactly why in a minute."
    )
    pdf.say(
        "Alright, Ajer is going to take you through the new features now."
    )

    # ══════════════════════════════════════════════════════════
    # 3. REVENUE AT RISK
    # ══════════════════════════════════════════════════════════
    pdf.section_header("3. REVENUE AT RISK")
    pdf.speaker("AJER")
    pdf.action("Click the Revenue at Risk tab.")

    pdf.note(
        "Note for us: Augie thinks in dollars. Lead with the big number, then break it down. "
        "The key surprise is that stalled loans are the biggest risk, not lock issues."
    )

    pdf.say(
        "This tab answers a simple question: how much money in the pipeline is in danger "
        "of not funding, and why? The answer is $145 million at risk, broken into 4 categories."
    )
    pdf.say(
        "The biggest category is Stalled High-Value Loans -- 97 loans totaling $79 million. "
        "These are above-median loan amounts that have been sitting at the same stage for "
        "30 or more days with no movement. The recommended action is priority escalation -- "
        "clear the outstanding conditions or re-engage the borrower directly."
    )
    pdf.say(
        "Second is Low Probability, High Value -- 47 loans, $64 million. These are large loans "
        "the model gives less than a 25% chance. They need a viability check -- either push "
        "them forward or stop spending ops time on them."
    )
    pdf.say(
        "Third, Rate Lock Expiring -- 7 loans, $1.5 million. Locks expiring within 7 days "
        "and the loan hasn't reached CTC yet. Action is to expedite underwriting or extend "
        "the lock."
    )
    pdf.say(
        "Fourth, No Lock at Late Stage -- 3 loans, $443 thousand. Past Approved without a "
        "rate lock, which is unusual. Action is to contact the borrower and get that locked."
    )
    pdf.action("Scroll down to the Recovery Opportunities table.")
    pdf.say(
        "Below the categories is a table of the top 12 individual recovery opportunities. "
        "These are specific loans ranked by recovery gap -- the difference between the full "
        "loan amount and what the model expects to fund. The top loan is a $4 million "
        "NONCONFORMING sitting at Approved with only 16% probability. That's a $3.3 million "
        "gap. If ops can move that one loan forward, it's worth $3.3 million. Total recovery "
        "potential across the top 12 is $10.4 million."
    )

    pdf.note(
        "Note for us: If Augie asks why so much is 'at risk' -- the $145M is the gap between "
        "full loan amounts and expected funded amounts. It's not that $145M will be lost. "
        "It's the theoretical ceiling of what could fund if every loan closed at 100%."
    )

    pdf.say(
        "So that's the risk picture -- where the money is, and what's threatening it. "
        "Now let me show you where in the pipeline these problems are actually happening."
    )

    # ══════════════════════════════════════════════════════════
    # 4. PIPELINE HEALTH
    # ══════════════════════════════════════════════════════════
    pdf.section_header("4. PIPELINE HEALTH")
    pdf.speaker("AJER")
    pdf.action("Click the Pipeline Health tab.")

    pdf.say(
        "This tab has four sections. Top left is the Bottleneck Heatmap -- it shows the "
        "median number of days each stage transition takes, broken down by product."
    )
    pdf.say(
        "The big number here is Approved to CTC: 18 days median. That's where the pipeline "
        "spends the most time. VA loans are worse at 20 days, 2ND products at 21. Compare "
        "that to Open-to-Submitted which is basically instant, and CTC-to-Funded which is "
        "5 days. The bottleneck is clearly in the middle of the pipeline."
    )
    pdf.say(
        "Top right is the Conversion Funnel. Of all loans that reach each stage, this "
        "shows what percent ultimately fund. There's a clear cliff: Submitted is only 50% -- "
        "half the loans that get submitted never fund. Approved is 69%. But once you get past "
        "Condition Review at 92%, it's almost certain. CTC is 99%. The battle is won or lost "
        "between Submitted and Condition Review."
    )
    pdf.action("Point to the bottom-left velocity distribution.")
    pdf.say(
        "Bottom left shows loan velocity -- how fast loans are moving through stages. "
        "62% of the pipeline is classified as Slow, that's $92 million. Another 28% is "
        "Stalled at $42 million. Only about 10% is moving at a healthy pace."
    )
    pdf.action("Point to the bottom-right bottleneck section.")
    pdf.say(
        "And bottom right confirms it. The Approved stage is highlighted red: 425 loans, "
        "$122 million, averaging 36 days sitting there, with 42% of them past 30 days. "
        "That is the chokepoint."
    )
    pdf.say(
        "So we've identified the bottleneck. The next question is: what happens if we fix it?"
    )

    # ══════════════════════════════════════════════════════════
    # 5. WHAT-IF SCENARIOS
    # ══════════════════════════════════════════════════════════
    pdf.section_header("5. WHAT-IF SCENARIOS")
    pdf.speaker("AJER")
    pdf.action("Click the What-If tab.")

    pdf.note(
        "Note for us: The $22.6M lock rate number might get pushback. It assumes only 40% "
        "of unlocked loans would actually convert if locked, so it's already conservative. "
        "Be ready to explain that."
    )

    pdf.say(
        "This tab shows 4 operational levers with pre-calculated dollar impact. These aren't "
        "hypothetical -- they're calculated from actual pipeline data and the model's scores."
    )
    pdf.say(
        "The biggest lever is improving the lock rate on Approved-stage loans. Right now "
        "there are 292 unlocked loans at Approved. Their average funding probability is 7%. "
        "Locked loans at the same stage average 61%. Even if only 40% of those loans get "
        "locked, that's $22.6 million in additional projected funding."
    )
    pdf.say(
        "Second lever is accelerating Approved-to-CTC. If we can reduce cycle time at "
        "that bottleneck stage, more loans fund before locks expire or borrowers walk away. "
        "That's worth $9.8 million."
    )
    pdf.say(
        "Third is reactivating the stale pipeline -- 178 loans sitting 30-plus days at the "
        "same stage. Many are still viable but have gone quiet. A targeted re-engagement "
        "campaign is worth $5.8 million."
    )
    pdf.say(
        "Fourth is Retail channel optimization. Retail pull-through is at 5% versus "
        "Wholesale at 30%. Even closing half that gap adds $700 thousand."
    )
    pdf.say(
        "Total across all four levers: $38.9 million in potential upside, which is about "
        "120% above the current projection. Obviously you won't capture all of it "
        "simultaneously, but even 20 to 30% of that is significant."
    )
    pdf.say(
        "Now let me show you how the different products and channels compare."
    )

    # ══════════════════════════════════════════════════════════
    # 6. SCORECARDS
    # ══════════════════════════════════════════════════════════
    pdf.section_header("6. SCORECARDS")
    pdf.speaker("AJER")
    pdf.action("Click the Scorecards tab.")

    pdf.note(
        "Note for us: Augie specifically asked for product-level analysis back in the Feb call. "
        "He said 'I guarantee you product and purpose will add a lot of value.' This tab "
        "proves he was right. Frame it that way."
    )

    pdf.say(
        "This is the head-to-head comparison Augie asked for. Every product type ranked "
        "across pull-through rate, cycle time, average loan size, funded volume, and "
        "revenue efficiency."
    )
    pdf.action("Point at the NONCONFORMING row.")
    pdf.say(
        "NONCONFORMING is the clear number one. 40% pull-through, $573 thousand average "
        "loan, highest efficiency score. This is the money-making engine."
    )
    pdf.say(
        "Good news across the board -- the trend column shows all products improving. "
        "Recent 3 months versus prior 3 months, every product has an up arrow."
    )
    pdf.action("Scroll to the channel comparison.")
    pdf.say(
        "Channel comparison confirms what we already know: Wholesale is at 25% pull-through "
        "versus Retail at 6%. Wholesale is 649 loans, Retail is 59. The gap is real and "
        "the data backs it up."
    )
    pdf.action("Scroll to the Money Makers vs Drains ranking.")
    pdf.say(
        "The rankings at the bottom sort products by efficiency score -- that's pull-through "
        "rate times average loan amount. NONCONFORMING, CONFORMING, and FHA are the top tier. "
        "This helps prioritize where to focus origination."
    )
    pdf.say(
        "I'll hand it back to Liam to walk through the action recommendations."
    )

    # ══════════════════════════════════════════════════════════
    # 7. OPTIMIZATION RECOMMENDATIONS
    # ══════════════════════════════════════════════════════════
    pdf.section_header("7. OPTIMIZATION RECOMMENDATIONS")
    pdf.speaker("LIAM")
    pdf.action("Click back to the Overview tab. Scroll to the top.")

    pdf.note(
        "Note for us: This is the closer. Frame it as 'if you only look at one thing each "
        "morning, look at this.' This is what makes it operational, not just informational."
    )

    pdf.say(
        "This brings us back to the top of the Overview -- the This Week's Top Actions section. "
        "This is where everything comes together. The model identifies risks and bottlenecks, "
        "and this section distills it into a ranked action list."
    )
    pdf.say(
        "There are 6 actions, each with an estimated dollar impact, urgency level, and effort "
        "level. The actions are color-coded -- red means immediate, copper means this week, "
        "blue means this month."
    )
    pdf.action("Point at the top 2 or 3 recommendations.")
    pdf.say(
        "The top actions are things like securing rate locks on unlocked late-stage loans, "
        "rushing CTC for loans with expiring locks, and clearing conditions on near-certain "
        "loans that just need a push to fund. Each one tells you exactly how many loans are "
        "affected and the dollar value of acting."
    )
    pdf.say(
        "Total estimated impact across all 6 actions: $7.1 million. That's the near-term, "
        "actionable number. It's smaller than the $38.9 million from the What-If tab because "
        "these are specific immediate actions, not systemic improvements."
    )
    pdf.say(
        "The key point here is that this turns the model from a forecasting tool into a "
        "decision-making tool. It doesn't just tell you what will happen. It tells you "
        "what to do about it, ranked by dollar impact."
    )

    # ══════════════════════════════════════════════════════════
    # 8. EXISTING FEATURES
    # ══════════════════════════════════════════════════════════
    pdf.section_header("8. EXISTING FEATURES")
    pdf.speaker("LIAM")

    pdf.say(
        "Quick recap on the features that were already there. The Watch List tab has "
        "at-risk loans with specific risk reasons -- lock expiring, no lock at late stage, "
        "stalled progression, low probability. Plus the full live and dead loan tables."
    )
    pdf.say(
        "The Trends tab tracks pull-through rate over 24 months and shows cycle time "
        "distributions with SLA tracking -- currently 15% of loans exceed the 45-day SLA."
    )
    pdf.say(
        "And the elimination filter flags 36% of the pipeline as dead based on conservative "
        "rules. The historical funding rate for those flagged loans is under 2%. Removing "
        "them keeps the forecast honest."
    )

    # ══════════════════════════════════════════════════════════
    # 9. CLOSING
    # ══════════════════════════════════════════════════════════
    pdf.section_header("9. CLOSING")
    pdf.speaker("LIAM")

    pdf.say(
        "So to wrap up -- the dashboard now has 7 tabs covering forecasting, risk "
        "identification, bottleneck analysis, velocity tracking, scenario planning, "
        "product and channel comparisons, and specific action recommendations."
    )
    pdf.say(
        "We'd love your feedback. Which of these features are most useful to your team "
        "day to day? Are there any thresholds or categories we should adjust -- for example, "
        "should the stalled cutoff be 30 days or something different? And is there interest "
        "in integrating this into ThoughtSpot or delivering it another way?"
    )
    pdf.say(
        "We can also keep building. We have a few more features on the roadmap -- "
        "early warning alerts that predict which loans will become at-risk before they "
        "stall, and cohort analysis that tracks groups of loans through the pipeline."
    )
    pdf.say(
        "Open to questions."
    )

    pdf.note(
        "Likely questions to be ready for:\n"
        "- 'How often does this update?' -- Currently a snapshot. Can be automated daily or weekly.\n"
        "- 'Can we see individual loan details?' -- Yes, Watch List has loan-level data.\n"
        "- 'Are the What-If numbers realistic?' -- They use historical data with conservative "
        "assumptions (e.g., 40% lock conversion rate).\n"
        "- 'What about interest rates / macro?' -- Per Augie's direction, we kept it to "
        "internal pipeline data. Rates could be a Phase 2 add."
    )

    # ── Save ──
    pdf.output(OUTPUT_PATH)
    print(f"PDF saved to: {OUTPUT_PATH}")
    print(f"Pages: {pdf.page_no()}")


if __name__ == "__main__":
    build_pdf()
