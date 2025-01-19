import ParentComponent from "@/components/ParentComponent";

const Home: React.FC = () => {
  return (
    <div>
      <header style={styles.header}>
        <h1>Photon Bot for Stellar</h1>
      </header>
      <section style={styles.hero}>
        <h2>Welcome to Photon Bot for Stellar</h2>
        <p>Connect your Stellar wallet and link it to your Telegram account seamlessly.</p>
        <a href="#wallet-section">Get Started</a>
      </section>
      {/* Render the ParentComponent */}
      <section id="wallet-section" style={styles.section}>
        <ParentComponent />
      </section>
      <footer style={styles.footer}>
        <p>© 2025 Photon Bot for Stellar. All rights reserved.</p>
      </footer>
    </div>
  );
};

const styles = {
  header: {
    padding: "1rem",
    textAlign: "center" as const,
    backgroundColor: "#282c34",
    color: "white",
  },
  hero: {
    padding: "4rem 2rem",
    textAlign: "center" as const,
    backgroundColor: "#f0f0f0",
  },
  section: {
    padding: "4rem 2rem",
    textAlign: "center" as const,
    backgroundColor: "#ffffff",
  },
  footer: {
    padding: "1rem",
    textAlign: "center" as const,
    backgroundColor: "#282c34",
    color: "white",
  },
};

export default Home;
