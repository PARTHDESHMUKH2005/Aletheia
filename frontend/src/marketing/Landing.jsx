import { Link } from "react-router-dom";
import "./marketing.css";
import { Nav, Footer, Reveal, CountUp, SectionHead, DemoTag } from "./components/Basics.jsx";
import HeroFlow from "./components/HeroFlow.jsx";
import { DecisionMock, SignatureMock } from "./components/Mockups.jsx";
import { BarChart, Orbit, Marquee, StampStack } from "./components/Animations.jsx";
import { PhotoIllus, SliderIllus, ReceiptIllus, RecordIllus, ReuseIllus, UnsureIllus } from "./components/Illustrations.jsx";
import { CONTACT_EMAIL, demoTotals, marketFigures, wasteKinds, orgKinds } from "./data.js";
import { usePageSetup } from "./usePageSetup.js";

/* Headline options:
   1. "Route every scrap. Prove every handoff."
   2. "Waste goes somewhere. Now you can prove where."   <- used: names the problem and the promise in eight words.
   3. "The right buyer for your scrap, and the receipt to prove it."
*/

const features = [
  { title: "Snap a photo. Get a destination.", eyebrow: "Photo to decision", Illus: PhotoIllus,
    body: "Take a picture of the pile. Aletheia works out what it is, roughly how much there is, and where it should go, with the reasons written out in plain words." },
  { title: "Choose what matters today: money or carbon.", eyebrow: "Carbon slider", Illus: SliderIllus,
    body: "Slide toward money and it picks the best-paying buyer nearby. Slide toward carbon and it picks the route that saves the most emissions. You see the trade before you commit." },
  { title: "A receipt for every load.", eyebrow: "Receipt against dumping", Illus: ReceiptIllus,
    body: "Each route comes with a receipt: what would have happened by default, what you chose, and the difference in rupees and CO2e. A load that is on paper is much harder to quietly dump." },
  { title: "A record nobody can quietly edit.", eyebrow: "Tamper-evident record", Illus: RecordIllus,
    body: "Every handoff is written down in order: matched, collected, weighed, verified. Anyone with the record number can open the verify page and see whether a single step has changed." },
  { title: "Working equipment gets a second life.", eyebrow: "Reuse before recycle", Illus: ReuseIllus,
    body: "If a laptop or monitor still looks usable, Aletheia suggests reuse or donation before breaking it down. Storage drives need a recorded wipe before they leave the building." },
  { title: "When it is not sure, it says so.", eyebrow: "Knows when not to guess", Illus: UnsureIllus,
    body: "Low confidence, hazardous items or missing prices send the load to a person instead of a confident wrong answer. Waste outside its lane is turned away with a pointer to the right authority." },
];

export default function Landing() {
  usePageSetup("Aletheia · Route waste and prove it");
  return (
    <div className="al-root">
      <a className="al-skip" href="#al-main">Skip to content</a>
      <Nav />
      <main id="al-main">
        {/* 2. Hero */}
        <section className="al-hero">
          <div className="al-container al-hero-grid">
            <div className="al-hero-copy">
              <p className="al-eyebrow al-rise" style={{ animationDelay: "0ms" }}>Waste routing with a receipt</p>
              <h1 className="al-rise" style={{ animationDelay: "80ms" }}>Waste goes somewhere. <span>Now you can prove where.</span></h1>
              <p className="al-hero-sub al-rise" style={{ animationDelay: "160ms" }}>
                Aletheia looks at your waste, picks where it should go, and keeps a record of every handoff that anyone can check.
              </p>
              <div className="al-actions al-rise" style={{ animationDelay: "240ms" }}>
                <Link to="/dashboard" className="al-btn al-btn-primary al-btn-lg">Open the app</Link>
                <a href="#how" className="al-btn al-btn-secondary al-btn-lg">See how it works</a>
              </div>
            </div>
            <div className="al-hero-visual al-rise" style={{ animationDelay: "200ms" }}>
              <HeroFlow />
            </div>
          </div>
        </section>

        {/* 3. Built for */}
        <section className="al-builtfor" aria-labelledby="al-builtfor-h">
          <div className="al-container">
            <h2 id="al-builtfor-h">Built for the places that throw away the most</h2>
            <ul className="al-chips">
              {["Universities", "Manufacturers", "Data centers", "Offices"].map((c, i) => (
                <Reveal as="li" key={c} delay={i * 70} className="al-chip">{c}</Reveal>
              ))}
            </ul>
          </div>
        </section>

        {/* 4. Product preview */}
        <section className="al-section" id="product">
          <div className="al-container al-split">
            <div>
              <SectionHead eyebrow="The decision screen" title="Every load gets a destination and the reasons behind it.">
                This is the screen your team sees after a photo. Ranked buyers, the distance, the money, the carbon, and why the runner-up lost. Try the switch.
              </SectionHead>
              <Reveal className="al-checks">
                <p>Ranked options, not a single black box answer</p>
                <p>Plain reasons for every pick</p>
                <p>A receipt against the default outcome</p>
              </Reveal>
            </div>
            <Reveal delay={100}><DecisionMock /></Reveal>
          </div>
        </section>

        {/* 5. Bar chart */}
        <section className="al-section al-tint" id="how">
          <div className="al-container">
            <SectionHead eyebrow="What routing changes" title="The same pile, three different endings." center>
              Left alone, scrap goes to landfill or the cheapest informal buyer and earns nothing on record. Routed, it pays and it counts.
            </SectionHead>
            <Reveal><BarChart /></Reveal>
          </div>
        </section>

        {/* 6. Features */}
        <section className="al-section">
          <div className="al-container">
            <SectionHead eyebrow="How it works" title="Six things Aletheia does for you." />
            <div className="al-features">
              {features.map(({ title, eyebrow, body, Illus }, i) => (
                <article key={title} className={`al-feature ${i % 2 ? "al-flip" : ""}`}>
                  <Reveal className="al-feature-art"><Illus /></Reveal>
                  <Reveal className="al-feature-copy" delay={80}>
                    <p className="al-eyebrow">{String(i + 1).padStart(2, "0")} · {eyebrow}</p>
                    <h3>{title}</h3>
                    <p>{body}</p>
                  </Reveal>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* 7. Count-up stats (illustrative demo data) */}
        <section className="al-stats-band">
          <div className="al-container">
            <div className="al-stats">
              <div><strong><CountUp value={demoTotals.kg} suffix=" kg" /></strong><p>routed in one demo campus batch</p></div>
              <div><strong><CountUp value={demoTotals.inrMostMoney} prefix="₹" /></strong><p>recovered when set to most money</p></div>
              <div><strong><CountUp value={demoTotals.co2eMostCarbon} suffix=" kg" /></strong><p>CO2e avoided when set to most carbon</p></div>
              <div><strong><CountUp value={4} /></strong><p>handoffs on record for every load</p></div>
            </div>
            <DemoTag>Illustrative demo data · synthetic buyers and prices</DemoTag>
          </div>
        </section>

        {/* 8. Signature */}
        <section className="al-section">
          <div className="al-container">
            <SectionHead eyebrow="The Aletheia signature" title="A receipt you can hand to an auditor. A page anyone can check." center>
              Each load ends with a passport: where it came from, where it went, what it earned, and every handoff in between.
            </SectionHead>
            <Reveal><SignatureMock /></Reveal>
          </div>
        </section>

        {/* 9. Orbit */}
        <section className="al-section al-dark">
          <div className="al-container al-split al-split-orbit">
            <SectionHead eyebrow="One place for every stream" title="Metals, paper, electronics, batteries. One routine for all of it.">
              Each material has its own buyers, rules and risks. Aletheia keeps them in one place so your team follows one simple routine.
            </SectionHead>
            <Reveal delay={100}><Orbit /></Reveal>
          </div>
        </section>

        {/* 10. Marquee */}
        <section className="al-section al-marquee-section" aria-label="What Aletheia handles and who it is for">
          <Marquee rows={[{ label: "Kinds of waste handled", items: wasteKinds }, { label: "Kinds of organisations", items: orgKinds }]} />
        </section>

        {/* 11. Stamped papers */}
        <section className="al-section al-tint">
          <div className="al-container al-split">
            <Reveal className="al-stamp-card"><StampStack /></Reveal>
            <SectionHead eyebrow="Every handoff, recorded" title="Paperwork that does itself.">
              Each time the load changes hands, the step is stamped onto its record with the time and the weight. By the end you have a full paper trail, and nobody had to fill in a form.
            </SectionHead>
          </div>
        </section>

        {/* 12. Expert CTA */}
        <section className="al-section">
          <div className="al-container">
            <div className="al-expert">
              <div className="al-expert-copy">
                <p className="al-eyebrow">Talk to us</p>
                <h2>See a live demo with your own waste.</h2>
                <p>Bring a photo of what piles up on your campus or floor. We will route it with you, live, and walk through the receipt.</p>
                <a className="al-btn al-btn-light al-btn-lg" href={`mailto:${CONTACT_EMAIL}?subject=Aletheia%20demo`}>Book a demo</a>
              </div>
              <div className="al-placeholder" role="img" aria-label="Placeholder image">
                <span>PLACEHOLDER IMAGE</span><small>Team or on-site photo, 4:3</small>
              </div>
            </div>
          </div>
        </section>

        {/* 13. Second count-up row + final CTA */}
        <section className="al-section al-tint">
          <div className="al-container">
            <SectionHead eyebrow="Why it matters" title="The scale of the problem in India." center />
            <div className="al-stats al-stats-light">
              {marketFigures.slice(0, 4).map(f => (
                <div key={f.label}>
                  <strong><CountUp value={f.value} decimals={f.decimals} prefix={f.prefix} suffix={f.suffix} /></strong>
                  <p>{f.label}</p>
                  <small className="al-source"><a href={f.url} target="_blank" rel="noreferrer">{f.source}, {f.year}</a></small>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="al-final">
          <div className="al-container al-final-inner">
            <Reveal>
              <h2>Start with one photo.</h2>
              <p>Route your next load and keep the proof.</p>
              <div className="al-actions al-center">
                <Link to="/dashboard" className="al-btn al-btn-light al-btn-lg">Open the app</Link>
                <Link to="/about" className="al-btn al-btn-ghost al-btn-lg">About Aletheia</Link>
              </div>
            </Reveal>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
