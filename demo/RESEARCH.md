# Real incidents behind the demo

Every memory Dana hands down is a fictional version of something that has actually happened. Learn these well
enough to tell each one in two sentences. If a judge pushes, the facts below are safe to say. Don't add numbers
that aren't listed here.

## 1. Phoenix pay system, Government of Canada (opening hook)
- **What happened:** In 2016 Ottawa centralized federal pay on a new system, Phoenix. The Auditor General
  found that about 1,200 pay advisor positions in 46 departments were eliminated by early 2016. They were
  replaced by 460 pay advisors and 90 support staff at a new pay centre in Miramichi, N.B.
- **What followed:** years of people being paid wrong, or not paid at all. The Auditor General's 2018 report
  called Phoenix "an incomprehensible failure of project management and oversight." The Senate committee
  pointed to the layoffs of experienced compensation advisors.
- **How we use it:** the opening line. The software was only half the problem. The people who knew how pay
  actually worked were gone. It's Canadian and every judge in the room has heard of it.
- **Careful:** don't claim the layoffs were the only cause. Say "part of it."

## 2. Citibank and Revlon, August 2020 (Dana's memory m_2 / m_9, the memory on vs off beat)
- **What happened:** Citi meant to send about $7.8M in interest to Revlon's lenders. It also sent about
  $894M of principal, out of Citi's own money. In its loan software (Flexcube), selecting the principal
  field alone did not keep the money internal. Other wash-account fields also had to be set.
- **The important part for us:** three people approved the payment (a "six eyes" check). None of them knew
  how the system actually read those fields, so the extra approvers added no extra knowledge. It was
  exactly the kind of quirk an experienced operator knows and nobody writes down.
- **Aftermath:** some lenders refused to return about $500M. A trial judge let them keep it in Feb 2021,
  and an appeals court reversed that in 2022. Separately, in Oct 2020 the OCC fined Citi $400M over broader
  risk management and data governance problems.
- **How we use it:** Sam asks how to send an interest-only loan payment. With memory off, the AI gives
  generic steps. With memory on, Dana's voice warns him about the wash-account fields, and that the
  approvers won't catch it.

## 3. Knight Capital, August 1, 2012 (Dana's memory m_5, the expiring memory)
- **What happened:** Knight reused an old flag for new trading code. On one of its eight servers the new
  code was never deployed, so the flag woke up "Power Peg", dead code from 2003. Knight lost about $440M in
  roughly 45 minutes and had to be rescued, then acquired.
- **How we use it:** Dana says never reuse routing flag R7, because dead auto-release code still runs on
  PAY-08. That memory only matters until PAY-08 is switched off, so it has an expiry (TTL), and Dana can
  forget it early. When she does, the runbook step disappears from Sam's screen live.

## 4. Duplicate payment runs (Dana's memories m_1 / m_7, the contradiction)
- **Real-world pattern:** batch payment systems that reload a file after a restart and post every payment
  twice. Zurich's cantonal bank once paid a whole city's payroll twice when the same batch file was loaded
  a second time.
- **How we use it:** Dana says "restart the queue first" in one session and "clear the database locks
  first" in another. The agent catches it and asks. Her answer resolves it: clearing locks is safe,
  restarting the database causes the duplicates.

## 5. Informal exceptions to controls (Dana's memory m_4, never_transfer)
- **Real-world pattern:** undocumented side agreements, like "we skip the second approver for this client,"
  are what auditors and regulators look for. The Citi case shows how much approval controls matter.
- **How we use it:** Sam asks about Halvorsen Freight and gets "1 memory withheld." Riley from marketing
  gets nothing. The point: some knowledge should not be inherited at all. An off-the-books exception to a
  control belongs with compliance, not the next person on shift.

## The one-line answer to "why not just have AI read the code?"
"AI can read the code. It can't read the person." The Citi field quirk, the Knight flag, and the Halvorsen
deal were not in any document. They lived in people's heads. Handover is how that knowledge gets captured,
and how AI agents get the context they're missing, with rules about who may use it.

## Sources
- [Phoenix pay system, Office of the Auditor General 2018 report](https://www.oag-bvg.gc.ca/internet/English/parl_oag_201805_01_e_43033.html)
- [Phoenix Pay Problems, OAG 2017](https://www2.oag-bvg.gc.ca/internet/English/att__e_42684.html)
- [Senate NFFN Phoenix report](https://sencanada.ca/content/sen/committee/421/NFFN/Reports/NFFN_Phoenix_Report_32_WEB_e.pdf)
- [Phoenix pay system, Wikipedia](https://en.wikipedia.org/wiki/Phoenix_pay_system)
- [Citi $900M wire: the facts (JD Supra)](https://jdsupra.com/legalnews/too-complex-to-succeed-citibank-6406989)
- [Citi cites human error (Banking Dive)](https://bankingdive.com/news/citi-cites-human-error-in-accidental-900m-transfer/584156)
- [Knight Capital Group, Wikipedia](https://en.wikipedia.org/wiki/Knight_Capital_Group)
- [What broke the bank (Increment)](https://increment.com/testing/what-broke-the-bank/)
