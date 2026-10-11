import { Link } from "react-router-dom";
import "./marketing.css";
import { Nav, Footer, Reveal, CountUp, SectionHead, DemoTag, Mark } from "./components/Basics.jsx";
import { demoTotals, marketFigures } from "./data.js";
import { usePageSetup } from "./usePageSetup.js";

const pillars = [
  { n: "01", title: "Decides", body: "From one photo it names the material, estimates the amount and ranks the places it can go, with the money and carbon for each." },
  { n: "02", title: "Proves", body: "Every load gets a receipt and every handoff is written to a record that anyone can check from a public page." },
  { n: "03", title: "Refuses to guess", body: "When it is unsure, when an item is hazardous or a price is missing, it hands the load to a person instead of bluffing." },
];

const rows = [
  ["Says where each item should go, and why", "Yes, with reasons", "You search and compare", "Depends on who you ask"],
  ["Shows the money vs. carbon trade-off", "Yes, before you choose", "Price is the focus", "Rarely tracked"],
  ["Receipt for each load", "Yes", "Varies by platform", "Paper slips, if any"],
  ["A record anyone can check", "Public verify page", "Usually private", "Files and email"],
  ["Flags what it is unsure about", "Sends to a person", "Not usually offered", "Relies on experience"],
];

const team = ["Parth Deshmukh", "Keha Chopra", "Tarush Mohindru", "Abhinandan Kumar"];

const steps = [
  { title: "Take a photo", body: "Snap the pile and add the weight if you know it." },
  { title: "Pick the route", body: "See ranked buyers, choose money or carbon, and save your choice." },
  { title: "Record the handoffs", body: "Mark it matched, collected, weighed and verified. The receipt and record build themselves." },
];

const users = [
  { who: "Universities and colleges", use: "Labs, hostels and workshops produce scrap, paper and old computers every term. One routine for all of it, with records for the annual report." },
  { who: "Manufacturers", use: "Offcuts and metal scrap leave every week. Compare buyers on price and carbon, and keep weights on record." },
  { who: "Data centers", use: "Retired servers and drives need reuse checks and recorded wipes before anything leaves the floor." },
  { who: "Offices", use: "Paper, cardboard and old laptops, routed without a facilities team spending a day on calls." },
];

export default function About() {
  usePageSetup("About · Aletheia");
  return (
    <div className="al-root">
      <a className="al-skip" href="#al-main">Skip to content</a>
      <Nav />
      <main id="al-main">
        {/* Opening statement */}
        <section className="al-about-hero">
          <div className="al-container al-about-hero-inner">
            <p className="al-eyebrow al-rise">About</p>
            <h1 className="al-rise" style={{ animationDelay: "80ms" }}>Aletheia makes sure waste ends up where it should, and leaves proof that it did.</h1>
            <p className="al-hero-sub al-rise" style={{ animationDelay: "160ms" }}>
              Aletheia helps universities, companies and data centers route their waste to the right buyer or recycler, and keeps a record of every handoff. The name is Greek for truth, or literally, nothing hidden.
            </p>
          </div>
        </section>

        {/* The problem */}
        <section className="al-section">
          <div className="al-container al-split al-split-top">
            <SectionHead eyebrow="The problem" title="Today, institutional waste runs on phone calls and trust." />
            <div className="al-problem">
              {[
                ["Manual", "Someone calls around for a scrap dealer, takes whatever price is offered and moves on. The best buyer is rarely the one who answers."],
                ["Slow", "Piles wait in corridors and yards for weeks because nobody owns the decision or knows who accepts what."],
                ["Hard to prove", "Once the truck leaves, the trail ends. There is no simple way to show where it went or that it was not dumped."],
              ].map(([t, b], i) => (
                <Reveal key={t} delay={i * 80} className="al-problem-item"><h3>{t}</h3><p>{b}</p></Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* Market size */}
        <section className="al-section al-tint">
          <div className="al-container">
            <SectionHead eyebrow="Market size" title="A very large stream, mostly undocumented." center>
              These figures describe India's waste and scrap markets. Each one shows its source and year.
            </SectionHead>
            <div className="al-market">
              {marketFigures.map((f, i) => (
                <Reveal key={f.label} delay={i * 60} className="al-market-card">
                  <strong><CountUp value={f.value} decimals={f.decimals} prefix={f.prefix} suffix={f.suffix} /></strong>
                  <p>{f.label}</p>
                  <small className="al-source"><a href={f.url} target="_blank" rel="noreferrer">{f.source}</a> · {f.year}</small>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* How we stand out */}
        <section className="al-section">
          <div className="al-container">
            <SectionHead eyebrow="How we stand out" title="Three things, done properly." center />
            <div className="al-pillars">
              {pillars.map((p, i) => (
                <Reveal key={p.n} delay={i * 80} className="al-pillar">
                  <span>{p.n}</span><h3>{p.title}</h3><p>{p.body}</p>
                </Reveal>
              ))}
            </div>
            <Reveal className="al-compare-wrap">
              <table className="al-compare">
                <caption className="al-sr">How Aletheia compares with marketplaces and a manual process</caption>
                <thead><tr><th scope="col"><span className="al-sr">Capability</span></th><th scope="col" className="al-compare-us">Aletheia</th><th scope="col">Marketplaces</th><th scope="col">Manual process</th></tr></thead>
                <tbody>
                  {rows.map(([cap, us, mk, man]) => (
                    <tr key={cap}><th scope="row">{cap}</th><td className="al-compare-us">{us}</td><td>{mk}</td><td>{man}</td></tr>
                  ))}
                </tbody>
              </table>
              <p className="al-small-note">Marketplaces and manual processes are general categories, not specific companies.</p>
            </Reveal>
          </div>
        </section>

        {/* What changes */}
        <section className="al-stats-band">
          <div className="al-container">
            <h2 className="al-band-title">What changes for our users</h2>
            <div className="al-stats">
              <div><strong><CountUp value={demoTotals.inrMostMoney} prefix="₹" /></strong><p>money recovered from one {demoTotals.kg} kg demo batch</p><DemoTag>Illustrative demo data</DemoTag></div>
              <div><strong><CountUp value={demoTotals.co2eMostCarbon} suffix=" kg" /></strong><p>CO2e avoided from the same batch</p><DemoTag>Illustrative demo data</DemoTag></div>
              <div><strong><CountUp value={1} suffix=" photo" /></strong><p>is all it takes to start routing a load</p><DemoTag>Product behaviour</DemoTag></div>
              <div><strong><CountUp value={4} suffix="/4" /></strong><p>handoffs on record per load, ready for an audit</p><DemoTag>Product behaviour</DemoTag></div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="al-section">
          <div className="al-container">
            <SectionHead eyebrow="How it works" title="Three steps. No training needed." center />
            <ol className="al-steps">
              {steps.map((s, i) => (
                <Reveal as="li" key={s.title} delay={i * 90} className="al-step">
                  <span className="al-step-n">{i + 1}</span><h3>{s.title}</h3><p>{s.body}</p>
                </Reveal>
              ))}
            </ol>
          </div>
        </section>

        {/* Who it is for */}
        <section className="al-section al-tint">
          <div className="al-container">
            <SectionHead eyebrow="Who it is for" title="Built for organisations with a steady stream of scrap." />
            <div className="al-users">
              {users.map((u, i) => (
                <Reveal key={u.who} delay={i * 70} className="al-user"><h3>{u.who}</h3><p>{u.use}</p></Reveal>
              ))}
            </div>
            <p className="al-small-note">Hospital and clinical waste is outside what Aletheia handles.</p>
          </div>
        </section>

        {/* Built to be trusted */}
        <section className="al-section" id="trust">
          <div className="al-container">
            <Reveal className="al-trust">
              <Mark size={44} />
              <div>
                <p className="al-eyebrow">Built to be trusted</p>
                <h2>An honest note on what this is.</h2>
                <ul>
                  <li>The demo uses synthetic buyers and illustrative prices. Real buyers and prices replace them in a live setup.</li>
                  <li>Aletheia routes and records. It is not legal advice and does not replace your own checks.</li>
                  <li>Always confirm rules and processor authorization with the official CPCB or State Board source.</li>
                  <li>When it is unsure, it says so and asks a person to decide.</li>
                </ul>
              </div>
            </Reveal>
          </div>
        </section>

        {/* Team */}
        <section className="al-section al-tint" id="team">
          <div className="al-container">
            <SectionHead eyebrow="Team" title="The people behind Aletheia." center />
            <div className="al-team">
              {team.map((name, i) => (
                <Reveal key={name} delay={i * 60} className="al-member">
                  <div className="al-avatar" aria-hidden="true">{name.split(" ").map(w => w[0]).join("")}</div>
                  <h3>{name}</h3>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="al-final">
          <div className="al-container al-final-inner">
            <Reveal>
              <h2>See where your waste really goes.</h2>
              <p>Open the app and route your next load.</p>
              <div className="al-actions al-center">
                <Link to="/dashboard" className="al-btn al-btn-light al-btn-lg">Open the app</Link>
                <Link to="/" className="al-btn al-btn-ghost al-btn-lg">Back to home</Link>
              </div>
            </Reveal>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
