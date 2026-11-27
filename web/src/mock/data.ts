/**
 * Mock data for RM Copilot. Synthetic: no real people, accounts or transactions.
 *
 * Screens read data only through the async getters at the bottom of this file.
 * When the app moves to Azure SQL (Lab 17), replace the getter bodies with
 * queries against the `app` views and keep the types and signatures.
 *
 * Signal rules mirrored here (from databricks/03_gold_build.ipynb):
 *   possible fraud   online, foreign merchant, R40,000 or more, 00:00 to 05:59 SAST
 *   forex growth     8 or more foreign travel transactions in the last 3 months
 *   idle cash        current account balance above 4 months of income
 *   salary increase  highest salary credit above the lowest
 *   upgrade          Private Banking client earning R92,000 or more a month
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SignalKind =
  | "possible_fraud"
  | "forex_growth"
  | "idle_cash"
  | "salary_increase"
  | "upgrade_candidate";

/** Risk signals are ranked above opportunities on the Today list. */
export type SignalCategory = "risk" | "opportunity";

export type Segment = "Private Banking" | "Signature";

/** The one number that matters for this signal. */
export type KeyFigure =
  | { kind: "amount"; value: number; caption: string }
  | { kind: "count"; value: number; unit: string; caption: string };

/**
 * The small chart drawn beside each call on Today. Series run over the same
 * 12 months as `MONTHS` (December 2025 to November 2026).
 */
export type Evidence =
  | {
      type: "night";
      /** Hours the client normally uses the card, e.g. [7, 21]. */
      usualHours: [number, number];
      events: { time: string; amount: number }[];
      description: string;
    }
  | {
      type: "bars" | "line" | "step";
      values: number[];
      /** Index of the first month that triggered the signal. */
      highlightFrom: number;
      threshold?: number;
      description: string;
    };

export type Signal = {
  kind: SignalKind;
  category: SignalCategory;
  /** Plain-language label shown under the client's name. */
  label: string;
  /** One sentence an RM can read at a glance. */
  reason: string;
  /** Clause for the Today summary when this client is first: "Start with X: <lead>." */
  lead: string;
  keyFigure: KeyFigure;
  evidence: Evidence;
};

export type RelationshipManager = {
  id: string;
  name: string;
  branch: string;
  clientCount: number;
  featured: boolean;
};

export type AccountType =
  | "Private Banking Account"
  | "Signature Account"
  | "Savings"
  | "Notice deposit"
  | "Credit card"
  | "Home loan";

export type Account = {
  id: string;
  type: AccountType;
  /** Masked number, e.g. "•••• 4821". */
  number: string;
  /** Positive for money the client holds, negative for money owed. */
  balance: number;
  /** Credit limit for cards; null where a limit does not apply. */
  limit: number | null;
};

export type Transaction = {
  id: string;
  /** ISO date-time in South African time (SAST). */
  at: string;
  description: string;
  direction: "in" | "out";
  amount: number;
  flagged: boolean;
};

export type MonthlySpend = { month: string; amount: number };

export type Brief = {
  whyCall: string;
  talkAbout: string[];
  watchOut: string;
  model: string;
  promptVersion: string;
  generatedAt: string;
};

export type Client = {
  id: string;
  name: string;
  segment: Segment;
  clientSince: number;
  rmId: string;
  monthlyIncome: number;
  signal: Signal | null;
  /** Today list position; null when the client is not on today's list. */
  rank: number | null;
  accounts: Account[];
  cardSpend: MonthlySpend[];
  /** Month (ISO date) whose card spend is out of pattern, if any. */
  anomalyMonth: string | null;
  transactions: Transaction[];
  brief: Brief | null;
};

/** A row in the Clients table: what the book view needs, nothing more. */
export type ClientRow = {
  id: string;
  name: string;
  segment: Segment;
  clientSince: number;
  signal: { kind: SignalKind; label: string; category: SignalCategory } | null;
  totalHeld: number;
  cardUtilisation: number | null;
};

export type TodaySummary = {
  asOf: string;
  runFinishedAt: string;
  risk: number;
  opportunities: number;
  quiet: number;
  bookSize: number;
};

export type BriefLogEntry = {
  id: string;
  at: string;
  clientId: string;
  clientName: string;
  signalLabel: string | null;
  model: string;
  promptVersion: string;
  inputTokens: number;
  outputTokens: number;
  /** True when an earlier brief from the same day was reused instead of a new call. */
  reused: boolean;
};

export type SignalRule = {
  kind: SignalKind;
  label: string;
  rule: string;
  scoredOn: string;
  result: string;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Date of the overnight run: Friday 27 November 2026. */
export const AS_OF = "2026-11-27";
export const RUN_FINISHED_AT = "2026-11-27T05:44:00";
export const MODEL = "deepseek-flash";
export const PROMPT_VERSION = "v6";
export const UPGRADE_THRESHOLD = 92000;

/** The 12 months every series covers, as ISO dates (first of the month). */
export const MONTHS: string[] = Array.from({ length: 12 }, (_, i) =>
  new Date(Date.UTC(2025, 11 + i, 1)).toISOString().slice(0, 10),
);

const months = (amounts: number[]): MonthlySpend[] =>
  amounts.map((amount, i) => ({ month: MONTHS[i], amount }));

export const relationshipManagers: RelationshipManager[] = [
  { id: "rm-014", name: "Thandi Mokoena", branch: "Sandton", clientCount: 154, featured: true },
  { id: "rm-022", name: "Pieter van der Merwe", branch: "Stellenbosch", clientCount: 147, featured: false },
  { id: "rm-031", name: "Naledi Khumalo", branch: "Umhlanga", clientCount: 139, featured: false },
];

// ---------------------------------------------------------------------------
// The five demo clients, one per signal
// ---------------------------------------------------------------------------

const demoClients: Client[] = [
  {
    id: "c-10482",
    name: "Refilwe Dlamini",
    segment: "Signature",
    clientSince: 2016,
    rmId: "rm-014",
    monthlyIncome: 92400,
    rank: 1,
    signal: {
      kind: "possible_fraud",
      category: "risk",
      label: "Possible fraud",
      reason:
        "Three online card payments abroad between 01:00 and 04:00 last night, each over R40,000, at shops she has never used.",
      lead: "her card was used three times overnight, at shops she has never used",
      keyFigure: { kind: "amount", value: 145765, caption: "3 payments, 01:12 to 03:58" },
      evidence: {
        type: "night",
        usualHours: [7, 21],
        events: [
          { time: "01:12", amount: 48250 },
          { time: "02:47", amount: 52900 },
          { time: "03:58", amount: 44615 },
        ],
        description:
          "Last 24 hours. She normally uses her card between 07:00 and 21:00. Three payments at 01:12, 02:47 and 03:58.",
      },
    },
    accounts: [
      { id: "a-1", type: "Signature Account", number: "•••• 4821", balance: 104221.86, limit: null },
      { id: "a-2", type: "Savings", number: "•••• 7730", balance: 286450.0, limit: null },
      { id: "a-3", type: "Credit card", number: "•••• 0915", balance: -186980.4, limit: 250000 },
    ],
    cardSpend: months([
      21480.5, 19870.2, 23110.75, 20540.0, 22315.4, 18990.6, 21760.85, 20125.3, 22840.1,
      21390.45, 19655.0, 166105.3,
    ]),
    anomalyMonth: "2026-11-01",
    transactions: [
      { id: "t-01", at: "2026-11-27T03:58:00", description: "Orbix Online, Cyprus", direction: "out", amount: 44615.0, flagged: true },
      { id: "t-02", at: "2026-11-27T02:47:00", description: "QuickBuy Global Ltd, United Kingdom", direction: "out", amount: 52900.0, flagged: true },
      { id: "t-03", at: "2026-11-27T01:12:00", description: "Nuvexa Digital, Malta", direction: "out", amount: 48250.0, flagged: true },
      { id: "t-04", at: "2026-11-26T18:34:00", description: "Woolworths Hyde Park", direction: "out", amount: 1284.65, flagged: false },
      { id: "t-05", at: "2026-11-26T12:05:00", description: "Vida e Caffè Rosebank", direction: "out", amount: 74.0, flagged: false },
      { id: "t-06", at: "2026-11-25T19:41:00", description: "Uber trip", direction: "out", amount: 186.4, flagged: false },
      { id: "t-07", at: "2026-11-25T08:00:00", description: "Salary: Mabena Attorneys", direction: "in", amount: 92400.0, flagged: false },
      { id: "t-08", at: "2026-11-24T17:20:00", description: "Engen Bryanston", direction: "out", amount: 1150.0, flagged: false },
      { id: "t-09", at: "2026-11-23T10:15:00", description: "Checkers Sixty60", direction: "out", amount: 932.8, flagged: false },
      { id: "t-10", at: "2026-11-22T20:02:00", description: "Netflix", direction: "out", amount: 199.0, flagged: false },
      { id: "t-11", at: "2026-11-21T13:30:00", description: "Dis-Chem Sandton City", direction: "out", amount: 642.15, flagged: false },
      { id: "t-12", at: "2026-11-20T09:45:00", description: "Transfer to savings", direction: "out", amount: 10000.0, flagged: false },
      { id: "t-13", at: "2026-11-19T19:10:00", description: "Mugg & Bean Melrose Arch", direction: "out", amount: 318.5, flagged: false },
      { id: "t-14", at: "2026-11-18T07:55:00", description: "Virgin Active", direction: "out", amount: 899.0, flagged: false },
      { id: "t-15", at: "2026-11-16T11:20:00", description: "Exclusive Books Hyde Park", direction: "out", amount: 465.0, flagged: false },
      { id: "t-16", at: "2026-11-14T13:05:00", description: "Tashas Rosebank", direction: "out", amount: 389.0, flagged: false },
      { id: "t-17", at: "2026-11-12T16:40:00", description: "Woolworths Hyde Park", direction: "out", amount: 2104.3, flagged: false },
      { id: "t-18", at: "2026-11-10T09:15:00", description: "Discovery Health", direction: "out", amount: 5980.0, flagged: false },
      { id: "t-19", at: "2026-11-07T18:25:00", description: "Engen Bryanston", direction: "out", amount: 1080.0, flagged: false },
      { id: "t-20", at: "2026-11-05T12:50:00", description: "Clicks Rosebank", direction: "out", amount: 312.6, flagged: false },
      { id: "t-21", at: "2026-11-02T10:00:00", description: "City of Johannesburg", direction: "out", amount: 3640.0, flagged: false },
    ],
    brief: {
      whyCall:
        "Three online card payments totalling R145,765.00 went through between 01:00 and 04:00 last night, to merchants in Malta, the United Kingdom and Cyprus that Refilwe has never paid before. She normally uses her card between 07:00 and 21:00, in Sandton and Rosebank.",
      talkAbout: [
        "Confirm whether she made the payments to Nuvexa Digital, QuickBuy Global Ltd and Orbix Online.",
        "If she did not, block the card ending 0915 and open a dispute for all three.",
        "Her card is now at 75% of its R250,000.00 limit. Discuss the limit only once the card is safe.",
      ],
      watchOut:
        "Never ask her to read out card details or a one-time PIN on the call. Use the bank's verification steps.",
      model: MODEL,
      promptVersion: PROMPT_VERSION,
      generatedAt: "2026-11-27T05:42:00",
    },
  },
  {
    id: "c-20517",
    name: "Thabo Nkosi",
    segment: "Private Banking",
    clientSince: 2012,
    rmId: "rm-014",
    monthlyIncome: 78500,
    rank: 2,
    signal: {
      kind: "idle_cash",
      category: "opportunity",
      label: "Idle cash",
      reason:
        "Over R1.2m has sat in his current account since April. That is 15 months of his income, earning almost nothing.",
      lead: "over R1.2m has sat untouched in his current account for eight months",
      keyFigure: { kind: "amount", value: 1214560.0, caption: "15.5 months of income" },
      evidence: {
        type: "line",
        values: [286000, 301000, 295000, 1180000, 1195000, 1201000, 1188000, 1204000, 1199000, 1210000, 1207000, 1214560],
        highlightFrom: 4,
        threshold: 314000,
        description:
          "Current account balance over 12 months. Above R1.1m every month since April; the dashed line is four months of income.",
      },
    },
    accounts: [
      { id: "a-1", type: "Private Banking Account", number: "•••• 3307", balance: 1214560.0, limit: null },
      { id: "a-2", type: "Credit card", number: "•••• 6142", balance: -8420.55, limit: 120000 },
      { id: "a-3", type: "Home loan", number: "•••• 5190", balance: -1830400.0, limit: null },
    ],
    cardSpend: months([
      9870.4, 11240.0, 8960.25, 10315.8, 9540.6, 10880.15, 9215.0, 10040.3, 9775.9, 10602.45,
      9330.2, 8420.55,
    ]),
    anomalyMonth: null,
    transactions: [
      { id: "t-01", at: "2026-11-26T15:22:00", description: "Pick n Pay Fourways", direction: "out", amount: 1342.8, flagged: false },
      { id: "t-02", at: "2026-11-25T09:10:00", description: "Home loan repayment", direction: "out", amount: 21460.0, flagged: false },
      { id: "t-03", at: "2026-11-25T08:00:00", description: "Salary: Nkosi Engineering", direction: "in", amount: 78500.0, flagged: false },
      { id: "t-04", at: "2026-11-22T11:48:00", description: "Builders Warehouse Fourways", direction: "out", amount: 2875.0, flagged: false },
      { id: "t-05", at: "2026-11-20T18:15:00", description: "Spur Steak Ranches", direction: "out", amount: 684.0, flagged: false },
      { id: "t-06", at: "2026-11-18T07:30:00", description: "Discovery Health", direction: "out", amount: 6120.0, flagged: false },
      { id: "t-07", at: "2026-11-12T17:05:00", description: "Engen Fourways", direction: "out", amount: 1240.0, flagged: false },
      { id: "t-08", at: "2026-11-03T10:30:00", description: "City of Johannesburg", direction: "out", amount: 4120.0, flagged: false },
    ],
    brief: {
      whyCall:
        "Thabo has kept between R1.18m and R1.22m in his current account since April, about 15 months of his income. In a 32-day notice deposit that cash could earn roughly R7,000.00 a month.",
      talkAbout: [
        "Ask whether the money is set aside for something specific, such as a property or business payment.",
        "If it is not needed soon, compare a 32-day notice deposit with a money market account.",
        "Leave enough in the current account to cover his R21,460.00 home loan repayment.",
      ],
      watchOut:
        "Do not recommend specific investments on this call. Refer him to a financial adviser for that.",
      model: MODEL,
      promptVersion: PROMPT_VERSION,
      generatedAt: "2026-11-27T05:43:00",
    },
  },
  {
    id: "c-31205",
    name: "Johan Pretorius",
    segment: "Signature",
    clientSince: 2019,
    rmId: "rm-014",
    monthlyIncome: 104800,
    rank: 3,
    signal: {
      kind: "forex_growth",
      category: "opportunity",
      label: "Forex growth",
      reason:
        "Nine trips abroad in the last three months, up from one in the first three. He pays conversion fees on each.",
      lead: "he has travelled abroad nine times in three months",
      keyFigure: { kind: "count", value: 9, unit: "trips", caption: "last 3 months, up from 1" },
      evidence: {
        type: "bars",
        values: [1, 0, 0, 0, 1, 0, 0, 1, 0, 3, 3, 3],
        highlightFrom: 9,
        description:
          "Foreign travel transactions per month. One from December to February; nine from September to November.",
      },
    },
    accounts: [
      { id: "a-1", type: "Signature Account", number: "•••• 2264", balance: 187340.12, limit: null },
      { id: "a-2", type: "Credit card", number: "•••• 8873", balance: -46215.9, limit: 150000 },
    ],
    cardSpend: months([
      14200.0, 13650.4, 15120.3, 14870.0, 16440.75, 15980.2, 17210.5, 18450.0, 21280.6, 38940.25,
      42115.8, 46215.9,
    ]),
    anomalyMonth: null,
    transactions: [
      { id: "t-01", at: "2026-11-24T21:14:00", description: "Heathrow Express, London (GBP)", direction: "out", amount: 612.4, flagged: false },
      { id: "t-02", at: "2026-11-24T13:02:00", description: "Pret A Manger, London (GBP)", direction: "out", amount: 248.9, flagged: false },
      { id: "t-03", at: "2026-11-17T19:40:00", description: "Hotel Okura, Amsterdam (EUR)", direction: "out", amount: 11840.0, flagged: false },
      { id: "t-04", at: "2026-11-10T09:25:00", description: "Emirates", direction: "out", amount: 18650.0, flagged: false },
      { id: "t-05", at: "2026-11-02T16:55:00", description: "Marriott, Dubai (AED)", direction: "out", amount: 9215.3, flagged: false },
      { id: "t-06", at: "2026-10-25T08:00:00", description: "Salary: Kloof Logistics", direction: "in", amount: 104800.0, flagged: false },
      { id: "t-07", at: "2026-10-19T08:40:00", description: "Schiphol Airport, Amsterdam (EUR)", direction: "out", amount: 1320.5, flagged: false },
      { id: "t-08", at: "2026-10-06T22:10:00", description: "The Savoy, London (GBP)", direction: "out", amount: 16480.0, flagged: false },
    ],
    brief: {
      whyCall:
        "Johan has made nine trips abroad since September, to London, Amsterdam and Dubai, against one trip from December to February. He pays card conversion fees in pounds, euros and dirhams each time.",
      talkAbout: [
        "Ask whether the travel is for work and whether it will continue.",
        "Show what a multi-currency travel wallet would have saved him on conversion fees.",
        "Check that his travel insurance covers this many trips a year.",
      ],
      watchOut:
        "His card spend has more than doubled since August. Confirm the travel is planned before discussing a higher limit.",
      model: MODEL,
      promptVersion: PROMPT_VERSION,
      generatedAt: "2026-11-27T05:43:00",
    },
  },
  {
    id: "c-44890",
    name: "Lerato Mahlangu",
    segment: "Private Banking",
    clientSince: 2021,
    rmId: "rm-014",
    monthlyIncome: 84250,
    rank: 4,
    signal: {
      kind: "salary_increase",
      category: "opportunity",
      label: "Salary increase",
      reason:
        "Her salary went up 23% in October, from R68,500 to R84,250. A good time to review her savings and cover.",
      lead: "her salary went up 23% in October",
      keyFigure: { kind: "amount", value: 84250.0, caption: "monthly salary, up 23%" },
      evidence: {
        type: "step",
        values: [68500, 68500, 68500, 68500, 68500, 68500, 68500, 68500, 68500, 68500, 84250, 84250],
        highlightFrom: 10,
        description: "Monthly salary credits. R68,500 until September, R84,250 from October.",
      },
    },
    accounts: [
      { id: "a-1", type: "Private Banking Account", number: "•••• 9018", balance: 64780.44, limit: null },
      { id: "a-2", type: "Savings", number: "•••• 1146", balance: 42300.0, limit: null },
      { id: "a-3", type: "Credit card", number: "•••• 3359", balance: -12890.2, limit: 45000 },
    ],
    cardSpend: months([
      11320.4, 10875.0, 12040.6, 11590.2, 10960.35, 11780.0, 12215.8, 11430.5, 11905.1, 12660.0,
      13120.45, 12890.2,
    ]),
    anomalyMonth: null,
    transactions: [
      { id: "t-01", at: "2026-11-25T10:30:00", description: "Transfer to savings", direction: "out", amount: 3000.0, flagged: false },
      { id: "t-02", at: "2026-11-25T08:00:00", description: "Salary: Sasol Group Services", direction: "in", amount: 84250.0, flagged: false },
      { id: "t-03", at: "2026-11-21T17:45:00", description: "Mr Price Home Rosebank", direction: "out", amount: 1460.0, flagged: false },
      { id: "t-04", at: "2026-11-14T12:30:00", description: "Woolworths Rosebank", direction: "out", amount: 876.35, flagged: false },
      { id: "t-05", at: "2026-10-25T08:00:00", description: "Salary: Sasol Group Services", direction: "in", amount: 84250.0, flagged: false },
      { id: "t-06", at: "2026-09-25T08:00:00", description: "Salary: Sasol Group Services", direction: "in", amount: 68500.0, flagged: false },
    ],
    brief: {
      whyCall:
        "Lerato's salary rose from R68,500.00 to R84,250.00 in October, but she still moves only R3,000.00 a month into savings.",
      talkAbout: [
        "Congratulate her on the increase and ask what she is planning for.",
        "Suggest raising her monthly savings transfer, or opening a tax-free savings account if she has none.",
        "Review her life and disability cover against the new salary.",
      ],
      watchOut: "Keep it a conversation, not a sales pitch. This is the first call since her increase.",
      model: MODEL,
      promptVersion: PROMPT_VERSION,
      generatedAt: "2026-11-27T05:44:00",
    },
  },
  {
    id: "c-52673",
    name: "Sipho Ndlovu",
    segment: "Private Banking",
    clientSince: 2020,
    rmId: "rm-014",
    monthlyIncome: 96400,
    rank: 5,
    signal: {
      kind: "upgrade_candidate",
      category: "opportunity",
      label: "Upgrade candidate",
      reason:
        "He now earns R96,400 a month, above the R92,000 where Signature starts, and is still on Private Banking.",
      lead: "his income now qualifies him for Signature",
      keyFigure: { kind: "amount", value: 96400.0, caption: "monthly income, Signature from R92,000" },
      evidence: {
        type: "line",
        values: [81200, 81200, 81200, 81200, 88600, 88600, 88600, 88600, 96400, 96400, 96400, 96400],
        highlightFrom: 8,
        threshold: UPGRADE_THRESHOLD,
        description:
          "Monthly income over 12 months. Above the R92,000 Signature threshold, the dashed line, since August.",
      },
    },
    accounts: [
      { id: "a-1", type: "Private Banking Account", number: "•••• 6620", balance: 312840.75, limit: null },
      { id: "a-2", type: "Notice deposit", number: "•••• 4471", balance: 650000.0, limit: null },
      { id: "a-3", type: "Savings", number: "•••• 2083", balance: 223459.25, limit: null },
      { id: "a-4", type: "Credit card", number: "•••• 7714", balance: -24610.0, limit: 80000 },
    ],
    cardSpend: months([
      22410.0, 21875.5, 23940.2, 22105.0, 24360.8, 23015.45, 22780.0, 24910.3, 23650.15, 25120.0,
      24380.6, 24610.0,
    ]),
    anomalyMonth: null,
    transactions: [
      { id: "t-01", at: "2026-11-26T14:10:00", description: "Tashas Morningside", direction: "out", amount: 512.0, flagged: false },
      { id: "t-02", at: "2026-11-25T08:00:00", description: "Salary: Ndlovu & Partners Inc", direction: "in", amount: 96400.0, flagged: false },
      { id: "t-03", at: "2026-11-24T09:00:00", description: "Transfer to notice deposit", direction: "out", amount: 20000.0, flagged: false },
      { id: "t-04", at: "2026-11-19T19:30:00", description: "Wine of the Month Club", direction: "out", amount: 1260.0, flagged: false },
      { id: "t-05", at: "2026-11-08T11:15:00", description: "Sandton Gautrain", direction: "out", amount: 180.0, flagged: false },
    ],
    brief: {
      whyCall:
        "Sipho's income rose to R96,400.00 a month in August, above the R92,000.00 where Signature starts. He is still on Private Banking.",
      talkAbout: [
        "Explain what changes on Signature: a dedicated RM, lower card fees and airport lounge access.",
        "Ask whether he would like his R650,000.00 notice deposit reviewed at the same time.",
      ],
      watchOut: "Check the Signature monthly fee against what he pays now before the call.",
      model: MODEL,
      promptVersion: PROMPT_VERSION,
      generatedAt: "2026-11-27T05:44:00",
    },
  },
];

// ---------------------------------------------------------------------------
// Quiet clients: generated, deterministic, no signal
// ---------------------------------------------------------------------------

function seeded(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const FIRST_NAMES = [
  "Ayanda", "Bongani", "Chantelle", "Daniel", "Elise", "Farah", "Gugu", "Hendrik", "Imran", "Jabu",
  "Karabo", "Lindiwe", "Mandla", "Nomsa", "Olwethu", "Priya", "Qhawe", "Ruan", "Sibusiso", "Tshepo",
  "Unathi", "Vusi", "Werner", "Xolani", "Yusuf", "Zanele", "Anika", "Kagiso", "Lebo", "Nadia",
  "Kabelo", "Megan", "Musa", "Palesa", "Riaan", "Siyabonga", "Thuli", "Zinhle", "Ashwin", "Mpho",
];
const SURNAMES = [
  "Botha", "Cele", "Daniels", "Essop", "Fourie", "Govender", "Hlongwane", "Jacobs", "Khoza", "Le Roux",
  "Mabaso", "Naidoo", "Molefe", "Pillay", "Radebe", "Sithole", "Tshabalala", "Venter", "Zulu", "Moodley",
  "Coetzee", "Dube", "Mthembu", "Nel", "Ntuli", "Shabalala", "Steyn", "Baloyi", "Maseko", "Kruger",
];
const MERCHANTS = [
  "Woolworths", "Pick n Pay", "Checkers", "Engen", "Shell", "Dis-Chem", "Clicks", "Uber trip",
  "Mugg & Bean", "Takealot", "Vida e Caffè", "Virgin Active", "Builders Warehouse", "Exclusive Books",
];
const EMPLOYERS = [
  "Standard Holdings", "Discovery Ltd", "Anglo Platinum", "MTN Group", "Investec Services",
  "Bidvest", "Netcare", "Shoprite Holdings", "Vodacom", "Old Mutual", "Deloitte Africa", "Absa Corporate",
];

const round2 = (n: number) => Math.round(n * 100) / 100;

function generateQuietClients(rmId: string, count: number, seed: number, idStart: number): Client[] {
  const rand = seeded(seed);
  const pick = <T,>(list: T[]) => list[Math.floor(rand() * list.length)];
  const used = new Set(demoClients.map((c) => c.name));
  const out: Client[] = [];

  for (let i = 0; i < count; i++) {
    let name = `${pick(FIRST_NAMES)} ${pick(SURNAMES)}`;
    while (used.has(name)) name = `${pick(FIRST_NAMES)} ${pick(SURNAMES)}`;
    used.add(name);

    // Keep quiet clients clear of every rule: Signature earners only, or
    // Private Banking under R92,000; current balance under 4 months of income.
    const signature = rand() < 0.35;
    const income = signature
      ? Math.round((92000 + rand() * 120000) / 100) * 100
      : Math.round((58000 + rand() * 33900) / 100) * 100;
    const segment: Segment = signature ? "Signature" : "Private Banking";
    const id = `c-${idStart + i * 7}`;
    const accounts: Account[] = [
      {
        id: "a-1",
        type: signature ? "Signature Account" : "Private Banking Account",
        number: `•••• ${String(1000 + Math.floor(rand() * 8999))}`,
        balance: round2(income * (0.4 + rand() * 3)),
        limit: null,
      },
    ];
    if (rand() < 0.6) {
      accounts.push({
        id: "a-2",
        type: "Savings",
        number: `•••• ${String(1000 + Math.floor(rand() * 8999))}`,
        balance: round2(income * (0.5 + rand() * 6)),
        limit: null,
      });
    }
    const limit = Math.round((income * (0.8 + rand() * 1.2)) / 5000) * 5000;
    const cardBase = income * (0.08 + rand() * 0.2);
    accounts.push({
      id: "a-3",
      type: "Credit card",
      number: `•••• ${String(1000 + Math.floor(rand() * 8999))}`,
      balance: -round2(Math.min(limit * 0.92, cardBase * (0.7 + rand() * 0.6))),
      limit,
    });
    if (rand() < 0.4) {
      accounts.push({
        id: "a-4",
        type: "Home loan",
        number: `•••• ${String(1000 + Math.floor(rand() * 8999))}`,
        balance: -Math.round(income * (8 + rand() * 20) / 100) * 100,
        limit: null,
      });
    }

    const employer = pick(EMPLOYERS);
    const transactions: Transaction[] = [
      { id: "t-01", at: "2026-11-25T08:00:00", description: `Salary: ${employer}`, direction: "in", amount: income, flagged: false },
    ];
    for (let t = 0; t < 7; t++) {
      const day = 26 - t * 3;
      const hour = 8 + Math.floor(rand() * 12);
      transactions.push({
        id: `t-${String(t + 2).padStart(2, "0")}`,
        at: `2026-11-${String(day).padStart(2, "0")}T${String(hour).padStart(2, "0")}:${String(Math.floor(rand() * 60)).padStart(2, "0")}:00`,
        description: pick(MERCHANTS),
        direction: "out",
        amount: round2(80 + rand() * 2400),
        flagged: false,
      });
    }
    transactions.sort((a, b) => b.at.localeCompare(a.at));

    out.push({
      id,
      name,
      segment,
      clientSince: 2008 + Math.floor(rand() * 17),
      rmId,
      monthlyIncome: income,
      signal: null,
      rank: null,
      accounts,
      cardSpend: months(MONTHS.map(() => round2(cardBase * (0.82 + rand() * 0.36)))),
      anomalyMonth: null,
      transactions,
      brief: null,
    });
  }
  return out;
}

const clients: Client[] = [
  ...demoClients,
  ...generateQuietClients("rm-014", 149, 42, 60011),
  ...generateQuietClients("rm-022", 147, 7, 70013),
  ...generateQuietClients("rm-031", 139, 11, 80017),
];

// ---------------------------------------------------------------------------
// Brief log and signal rules
// ---------------------------------------------------------------------------

const briefLog: BriefLogEntry[] = [
  { id: "b-2041", at: "2026-11-27T05:44:00", clientId: "c-52673", clientName: "Sipho Ndlovu", signalLabel: "Upgrade candidate", model: MODEL, promptVersion: PROMPT_VERSION, inputTokens: 1184, outputTokens: 212, reused: false },
  { id: "b-2040", at: "2026-11-27T05:44:00", clientId: "c-44890", clientName: "Lerato Mahlangu", signalLabel: "Salary increase", model: MODEL, promptVersion: PROMPT_VERSION, inputTokens: 1096, outputTokens: 198, reused: false },
  { id: "b-2039", at: "2026-11-27T05:43:00", clientId: "c-31205", clientName: "Johan Pretorius", signalLabel: "Forex growth", model: MODEL, promptVersion: PROMPT_VERSION, inputTokens: 1342, outputTokens: 231, reused: false },
  { id: "b-2038", at: "2026-11-27T05:43:00", clientId: "c-20517", clientName: "Thabo Nkosi", signalLabel: "Idle cash", model: MODEL, promptVersion: PROMPT_VERSION, inputTokens: 1128, outputTokens: 219, reused: false },
  { id: "b-2037", at: "2026-11-27T05:42:00", clientId: "c-10482", clientName: "Refilwe Dlamini", signalLabel: "Possible fraud", model: MODEL, promptVersion: PROMPT_VERSION, inputTokens: 1415, outputTokens: 244, reused: false },
  { id: "b-2031", at: "2026-11-26T09:18:00", clientId: "c-31205", clientName: "Johan Pretorius", signalLabel: "Forex growth", model: MODEL, promptVersion: PROMPT_VERSION, inputTokens: 1338, outputTokens: 0, reused: true },
  { id: "b-2024", at: "2026-11-26T05:41:00", clientId: "c-31205", clientName: "Johan Pretorius", signalLabel: "Forex growth", model: MODEL, promptVersion: PROMPT_VERSION, inputTokens: 1338, outputTokens: 226, reused: false },
  { id: "b-2019", at: "2026-11-25T14:02:00", clientId: "c-60011", clientName: "", signalLabel: null, model: MODEL, promptVersion: PROMPT_VERSION, inputTokens: 902, outputTokens: 174, reused: false },
  { id: "b-1987", at: "2026-11-23T05:40:00", clientId: "c-20517", clientName: "Thabo Nkosi", signalLabel: "Idle cash", model: MODEL, promptVersion: "v5", inputTokens: 1102, outputTokens: 247, reused: false },
];

const signalRules: SignalRule[] = [
  {
    kind: "possible_fraud",
    label: "Possible fraud",
    rule: "Online payment to a foreign merchant of R40,000 or more, between 00:00 and 05:59.",
    scoredOn: "Each transaction",
    result: "100%",
  },
  {
    kind: "idle_cash",
    label: "Idle cash",
    rule: "Current account balance above four months of the client's income.",
    scoredOn: "Each client",
    result: "100%",
  },
  {
    kind: "salary_increase",
    label: "Salary increase",
    rule: "The highest salary credit in 12 months is above the lowest.",
    scoredOn: "Each client",
    result: "100%",
  },
  {
    kind: "upgrade_candidate",
    label: "Upgrade candidate",
    rule: "Private Banking client earning R92,000 or more a month, where Signature starts.",
    scoredOn: "Each client",
    result: "100%",
  },
  {
    kind: "forex_growth",
    label: "Forex growth",
    rule: "Eight or more foreign travel transactions in the last three months.",
    scoredOn: "Each client",
    result: "about 99%",
  },
];

// ---------------------------------------------------------------------------
// Derived values
// ---------------------------------------------------------------------------

/** Money the client holds with the bank: the sum of positive balances. */
export function totalHeld(client: Pick<Client, "accounts">): number {
  return client.accounts.reduce((sum, a) => (a.balance > 0 ? sum + a.balance : sum), 0);
}

/** Money the client owes: the sum of negative balances, as a positive number. */
export function totalOwed(client: Pick<Client, "accounts">): number {
  return client.accounts.reduce((sum, a) => (a.balance < 0 ? sum - a.balance : sum), 0);
}

/** Credit card balance as a share of the limit, 0 to 1. Null when there is no card. */
export function cardUtilisation(client: Pick<Client, "accounts">): number | null {
  const card = client.accounts.find((a) => a.type === "Credit card" && a.limit);
  return card ? Math.abs(card.balance) / card.limit! : null;
}

// ---------------------------------------------------------------------------
// Getters: swap these bodies for SQL queries later. Keep the signatures.
// ---------------------------------------------------------------------------

export async function getRelationshipManagers(): Promise<RelationshipManager[]> {
  return relationshipManagers;
}

export async function getRelationshipManager(id: string): Promise<RelationshipManager | null> {
  return relationshipManagers.find((rm) => rm.id === id) ?? null;
}

export async function getFeaturedRelationshipManager(): Promise<RelationshipManager> {
  return relationshipManagers.find((rm) => rm.featured) ?? relationshipManagers[0];
}

/** Clients on today's call list, risk first, then by rank. */
export async function getTodayCalls(rmId: string): Promise<Client[]> {
  return clients
    .filter((c) => c.rmId === rmId && c.signal && c.rank !== null)
    .sort((a, b) => {
      const byCategory =
        Number(b.signal!.category === "risk") - Number(a.signal!.category === "risk");
      return byCategory || a.rank! - b.rank!;
    });
}

export async function getTodaySummary(rmId: string): Promise<TodaySummary> {
  const rm = await getRelationshipManager(rmId);
  const calls = await getTodayCalls(rmId);
  const risk = calls.filter((c) => c.signal!.category === "risk").length;
  const bookSize = rm?.clientCount ?? 0;
  return {
    asOf: AS_OF,
    runFinishedAt: RUN_FINISHED_AT,
    risk,
    opportunities: calls.length - risk,
    quiet: bookSize - calls.length,
    bookSize,
  };
}

/** The whole book for one RM, flagged clients first, then by name. */
export async function getClientBook(rmId: string): Promise<ClientRow[]> {
  return clients
    .filter((c) => c.rmId === rmId)
    .sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999) || a.name.localeCompare(b.name))
    .map((c) => ({
      id: c.id,
      name: c.name,
      segment: c.segment,
      clientSince: c.clientSince,
      signal: c.signal
        ? { kind: c.signal.kind, label: c.signal.label, category: c.signal.category }
        : null,
      totalHeld: totalHeld(c),
      cardUtilisation: cardUtilisation(c),
    }));
}

export async function getClient(id: string): Promise<Client | null> {
  return clients.find((c) => c.id === id) ?? null;
}

/**
 * The brief for a client. Flagged clients have one from the overnight run;
 * quiet clients get a routine check-in brief. Later this becomes the API
 * route that calls DeepSeek, reuses today's brief and logs the call.
 */
export async function getBrief(client: Client): Promise<Brief> {
  if (client.brief) return client.brief;
  const first = client.name.split(" ")[0];
  return {
    whyCall: `No signal for ${first} today. This is a routine check-in: the last 12 months of accounts and card use look steady.`,
    talkAbout: [
      `Ask whether anything has changed at work or at home that the bank should know about.`,
      `Confirm the contact details and the best time to reach ${first}.`,
    ],
    watchOut: "Keep it short. There is nothing urgent on this account.",
    model: MODEL,
    promptVersion: PROMPT_VERSION,
    generatedAt: `${AS_OF}T08:15:00`,
  };
}

export async function getBriefLog(): Promise<BriefLogEntry[]> {
  return briefLog.map((entry) =>
    entry.clientName
      ? entry
      : { ...entry, clientName: clients.find((c) => c.id === entry.clientId)?.name ?? "Unknown client" },
  );
}

export async function getSignalRules(): Promise<SignalRule[]> {
  return signalRules;
}
