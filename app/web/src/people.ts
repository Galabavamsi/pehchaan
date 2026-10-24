// The two people on the demo phones (SPEC §7 "Two people, two phones, both directions"). Fictional; mirrors the
// server's seed (app/server/pehchaan_api/scenarios.py). Each phone pays as its person and answers Family Verify
// for the other one.
import type { Relative } from "./api";

export type PersonKey = "sunita" | "rahul";
export interface PaidBefore { vpa: string; label: string; label_hi: string; times: number }
export interface Person {
  key: PersonKey;
  payer: { id: string; name: string; name_hi: string; vpa: string; vpa_masked: string; bank_name: string; bank_name_hi: string;
    phone: string; lang: "en" | "hi"; circle: Relative[] };
  /** This phone's entry in the other person's circle: the device that receives their Family Verify requests. */
  inbox: { relative: Relative; payerName: string; payerNameHi: string };
  paidBefore: PaidBefore[];
  blurb: string;
}

const RAHUL: Relative = {
  id: "rel_rahul", name: "Rahul", name_hi: "राहुल", full_name: "Rahul Sharma", relation: "son", relation_hi: "बेटा", pronoun: "he",
  device_id: "dev_rahul", saved_number: "+919829011223", lives_in: "London", calls_payer: "Mummy", calls_payer_hi: "मम्मी",
};
const PRIYA: Relative = {
  id: "rel_priya", name: "Priya", name_hi: "प्रिया", full_name: "Priya Sharma", relation: "daughter", relation_hi: "बेटी", pronoun: "she",
  device_id: "dev_priya", saved_number: "+919772033445", lives_in: "Pune", calls_payer: "Mummy", calls_payer_hi: "मम्मी",
};
const MUMMY: Relative = {
  id: "rel_sunita", name: "Mummy", name_hi: "मम्मी", full_name: "Sunita Sharma", relation: "mother", relation_hi: "माँ", pronoun: "she",
  device_id: "dev_sunita", saved_number: "+919812345210", lives_in: "Jaipur", calls_payer: "Rahul", calls_payer_hi: "राहुल",
};
const BANK = { bank_name: "Bharat Demo Bank", bank_name_hi: "भारत डेमो बैंक" };

export const PEOPLE: Record<PersonKey, Person> = {
  sunita: {
    key: "sunita", blurb: "Mummy, in Jaipur",
    payer: { id: "u_sunita", name: "Sunita Sharma", name_hi: "सुनीता शर्मा", vpa: "sunita.sharma@bdb", vpa_masked: "sunita.s•••@bdb",
      phone: "+919812345210", lang: "hi", circle: [RAHUL, PRIYA], ...BANK },
    inbox: { relative: MUMMY, payerName: "Rahul Sharma", payerNameHi: "राहुल शर्मा" },
    paidBefore: [
      { vpa: "rahul.s@bdb", label: "Rahul (beta)", label_hi: "राहुल (बेटा)", times: 6 },
      { vpa: "priya.sharma@okdemo", label: "Priya", label_hi: "प्रिया", times: 5 },
      { vpa: "meena.gupta@okdemo", label: "Meena Gupta", label_hi: "मीना गुप्ता", times: 4 },
      { vpa: "jvvnl.bill@okdemo", label: "Electricity bill", label_hi: "बिजली बिल", times: 12 },
    ],
  },
  rahul: {
    key: "rahul", blurb: "Her son, in London",
    payer: { id: "u_rahul", name: "Rahul Sharma", name_hi: "राहुल शर्मा", vpa: "rahul.s@bdb", vpa_masked: "rahul.s•••@bdb",
      phone: "+919829011223", lang: "en", circle: [MUMMY], ...BANK },
    inbox: { relative: RAHUL, payerName: "Sunita Sharma", payerNameHi: "सुनीता शर्मा" },
    paidBefore: [
      { vpa: "sunita.sharma@bdb", label: "Mummy", label_hi: "मम्मी", times: 3 },
      { vpa: "thames.lettings@okdemo", label: "Flat rent", label_hi: "मकान किराया", times: 10 },
      { vpa: "priya.sharma@okdemo", label: "Priya", label_hi: "प्रिया", times: 2 },
    ],
  },
};

const ME_KEY = "pehchaan.me";
/** Who uses this phone. Older installs saved a role: the payer was Sunita, the family phone was Rahul. */
export function savedPerson(): PersonKey | null {
  try {
    const me = localStorage.getItem(ME_KEY) as PersonKey | null;
    if (me === "sunita" || me === "rahul") return me;
    const role = localStorage.getItem("pehchaan.role");
    return role === "payer" ? "sunita" : role === "relative" ? "rahul" : null;
  } catch { return null; }
}
export function savePerson(k: PersonKey) { try { localStorage.setItem(ME_KEY, k); } catch { /* ignore */ } }
