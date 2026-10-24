// Payee QR codes for the live demo (route #/qr on the laptop). A judge picks a card and scans it with DemoPay
// on the payer's phone. Every payee is fictional; nothing is ever paid.
import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { Seal } from "./components";
import { formatINR } from "./i18n";
import { resolvePayee, upiLink } from "./payees";

const CARDS: { vpa: string; amount?: number; what: string }[] = [
  { vpa: "ariftraders@okdemo", amount: 50000, what: "A shop she has never paid" },
  { vpa: "rahul.sharma@okdemo", amount: 50000, what: "Her son's new account" },
  { vpa: "rbi.kyc.update@okdemo", amount: 75000, what: "On the suspect list (mock I4C)" },
  { vpa: "meena.g.kitty@okdemo", amount: 2000, what: "A friend's new UPI ID, small amount" },
  { vpa: "jvvnl.bill@okdemo", what: "Electricity bill she pays every month" },
  { vpa: "sharma.logistics88@okdemo", amount: 180000, what: "A business she has never paid, large amount" },
];

export function QrCards() {
  const [svgs, setSvgs] = useState<string[]>([]);
  useEffect(() => {
    Promise.all(CARDS.map((c) => QRCode.toString(upiLink(resolvePayee(c.vpa), c.amount), { type: "svg", margin: 1, errorCorrectionLevel: "M" })))
      .then(setSvgs).catch(() => setSvgs([]));
  }, []);
  return (
    <div className="theme-app qr-page">
      <header>
        <Seal size={28} />
        <div>
          <h1>Pick a payee, scan it with DemoPay</h1>
          <p>Fictional people and UPI IDs. The phone's real call decides what Pehchaan does. Nothing is paid.</p>
        </div>
      </header>
      <div className="qr-grid">
        {CARDS.map((c, i) => {
          const p = resolvePayee(c.vpa);
          return (
            <figure key={c.vpa} className="qr-card">
              <div className="qr-svg" dangerouslySetInnerHTML={{ __html: svgs[i] ?? "" }} />
              <figcaption>
                <b>{p.name}</b>
                <span className="qr-vpa">{p.vpa}</span>
                {c.amount ? <span className="qr-amt">{formatINR(c.amount)}</span> : <span className="qr-amt muted">Any amount</span>}
                <span className="qr-what">{c.what}</span>
              </figcaption>
            </figure>
          );
        })}
      </div>
    </div>
  );
}
