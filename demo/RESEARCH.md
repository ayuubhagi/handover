# Real incidents behind the demo (2024 to 2026)

Every memory Dana hands down is a fictional version of something that has really happened recently. Learn
these well enough to tell each one in two sentences. If a judge pushes, the facts below are safe to say.
Don't add numbers that aren't listed here.

## 1. Canada's federal early retirement wave, 2026 (opening hook)
- **What's happening:** Budget 2025 set out to shrink the federal public service, partly through an Early
  Retirement Incentive. About 68,000 public servants were told they might be eligible, and about 10,000
  applied. Approved employees have to retire by **January 20, 2027**, which is two months from now.
- **The knowledge problem:** the union for federal professionals (PIPSC) warned the program could hollow out
  the public service. Observers have flagged the loss of institutional knowledge.
- **How we use it:** the opening line. "Right now, thousands of Canada's most experienced public servants are
  retiring at once, and most of what they know isn't written down anywhere." It's current, it's in Canada, and
  the judges have read about it.
- **Careful:** it's a political topic. Stay neutral: we're not saying the policy is good or bad, only that the
  knowledge leaves with the people.

## 2. Citigroup's $81 trillion near miss, 2024 (Dana's memories m_2 / m_9, the memory on vs off beat)
- **What happened:** In April 2024 (reported by the Financial Times in February 2025), Citi meant to credit a
  client $280. The payment had been held by sanctions screening, so staff re-keyed it on a **rarely used backup
  screen**. That screen pre-filled the amount field with 15 zeros, and nobody deleted them. The client was
  credited $81 trillion.
- **The important part for us:** two people reviewed it and missed it. A third caught it about 90 minutes later,
  and it was reversed before any money left the bank. A quirk of a screen nobody uses is exactly the kind of
  thing only a veteran remembers.
- **How we use it:** Sam asks how to push a held payment through by hand. With memory off, the AI says
  "re-enter it manually and get it approved". With memory on, Dana's voice warns him about the pre-filled zeros,
  and that the approvers won't catch it.

## 3. "Why not just replace people with AI?" (Q&A ammunition)
- **Klarna, 2024 to 2025:** in 2024 Klarna said its AI assistant was doing the work of 700 customer service
  agents. In May 2025 its CEO said the push had gone too far, quality had dropped, and it started hiring humans
  again.
- **Commonwealth Bank of Australia, August 2025:** it cut 45 call centre jobs for an AI voice bot, then
  reversed the decision and called it an error, because call volumes went up instead of down.
- **How we use it:** we're not anti-AI. AI without the experts' knowledge gets things wrong. Handover is how the
  knowledge gets into the AI, with rules on who can use it.

## 4. Firing experts you can't replace quickly, February 2025 (Q&A ammunition)
- **What happened:** the US National Nuclear Security Administration laid off around 300 to 350 staff, then
  rehired almost all of them within days. Those roles need security clearances and training that can take up to
  18 months.
- **How we use it:** if a judge asks "can't you just retrain someone?", the answer is that some knowledge takes
  months or years to rebuild.

## 5. Legacy systems still run the banks (context for the R7 / PAY-08 memory)
- **What happened:** Barclays went down from January 31 to February 2, 2025, on payday weekend. Its CEO told
  Parliament the cause was a software fault in its UK mainframe. Barclays said it would pay £5 to £7.5 million in
  compensation.
- **How we use it:** old systems are still at the core of banks, and the people who understand their quirks are
  the ones retiring. Dana's warning about routing flag R7 and the old PAY-08 server is fictional, but it's that
  kind of knowledge. **Don't** say Barclays was caused by a reused flag. It wasn't.

## Patterns behind the other memories (no specific incident to cite)
- **Duplicate postings after a restart (m_1 / m_7, the contradiction):** batch systems that reload a file after a
  restart and post everything twice are a classic payments-ops failure.
- **Off-the-books exceptions to controls (m_4, never_transfer):** "we skip the second approver for this client"
  is what auditors look for. The Citi case shows why second approvals matter.

## The one-line answer to "why not just have AI read the code?"
"AI can read the code. It can't read the person." The backup-screen zeros, the R7 flag and the Halvorsen deal
aren't in any document. Klarna and Commonwealth Bank both learned that AI without that knowledge falls short.
Handover is how the knowledge gets captured, and how AI agents get the context they're missing, with rules
about who can use it.

## Sources
- [About 10,000 federal public servants apply for early retirement (CBC)](https://www.cbc.ca/news/canada/ottawa/canada-federal-public-service-cuts-early-retirement-9.7288822)
- [What you need to know about the early retirement package (CP24)](https://www.cp24.com/news/canada/2026/03/31/heres-what-you-need-to-know-about-the-federal-governments-early-retirement-package/)
- [Thousands approved for early retirement (CP24)](https://www.cp24.com/news/canada/2026/05/28/thousands-of-federal-public-servants-approved-for-early-retirement/)
- [Citigroup credited client account with $81tn in near miss (Irish Times, from the FT)](https://www.irishtimes.com/business/2025/02/28/citigroup-erroneously-credited-client-account-with-81tn-in-near-miss)
- [Citigroup nearly credited client $81 trillion instead of $280 (TechSpot)](https://www.techspot.com/news/106981-citigroup-nearly-credited-client-81-trillion-instead-of-280.html)
- [Klarna hiring customer service agents again (Entrepreneur)](https://www.entrepreneur.com/business-news/klarna-ceo-reverses-course-by-hiring-more-humans-not-ai/491396)
- [Australia's biggest bank reverses plan to replace jobs with AI (Bloomberg)](https://www.bloomberg.com/news/articles/2025-08-21/commonwealth-bank-reverses-job-cuts-decision-over-ai-chatbots)
- [CommBank reverses plan to replace call centre staff with AI (Finextra)](https://finextra.com/newsarticle/46482/commbank-reverses-plan-to-replace-call-centre-staff-with-ai)
- [Nuclear weapons workers fired, then rehired (CBS News)](https://www.cbsnews.com/news/doge-firings-us-nuclear-weapons-workers-reversing)
- [Barclays outage and legacy systems (GlobalData)](https://www.globaldata.com/media/banking/barclays-tech-outage-highlights-legacy-banking-system-risks-amid-rising-digital-competition-says-globaldata/)
- [Barclays pays millions in compensation after IT outage (BTW Media)](https://btw.media/en/barclays-pays-millions-in-customer-compensation-after-it-outage)
