import { NavBar } from "@/components/ui/NavBar";
import { Hero } from "@/components/sections/Hero";
import { Supports } from "@/components/sections/Supports";
import { Features } from "@/components/sections/Features";
import { HowItWorks } from "@/components/sections/HowItWorks";
import { Ethics } from "@/components/sections/Ethics";
import { FAQ } from "@/components/sections/FAQ";
import { Footer } from "@/components/sections/Footer";

export default function Page() {
  return (
    <>
      <NavBar />
      <main>
        <Hero />
        <Supports />
        <Features />
        <HowItWorks />
        <Ethics />
        <FAQ />
      </main>
      <Footer />
    </>
  );
}
