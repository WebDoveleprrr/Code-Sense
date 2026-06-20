import React, { useContext } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { Search, Building2, Zap, LayoutDashboard, Database, ArrowRight, ShieldAlert, GitBranch } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';

export default function LandingPage() {
  const { authenticated } = useContext(AuthContext);

  if (authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 font-sans selection:bg-indigo-500/30">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center">
            <Zap size={18} className="text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight">CodeSense</span>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/login" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
            Sign In
          </Link>
          <Link to="/dashboard" className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-full transition-all shadow-glow">
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <main className="px-8 pt-20 pb-32 max-w-7xl mx-auto text-center">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8">
          Understand Any Codebase <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-violet-400">
            with AI
          </span>
        </h1>
        <p className="text-lg md:text-xl text-slate-400 max-w-3xl mx-auto mb-10 leading-relaxed">
          Semantic Search, Architecture Analysis, Repository Q&A, Impact Analysis, and AI Code Review in one premium developer platform.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/login" className="px-8 py-4 text-base font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-full transition-all shadow-glow flex items-center gap-2 w-full sm:w-auto justify-center">
            Get Started <ArrowRight size={18} />
          </Link>
          <Link to="/dashboard" className="px-8 py-4 text-base font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-full transition-all w-full sm:w-auto justify-center flex items-center">
            Explore Demo Repository
          </Link>
        </div>
      </main>

      {/* Features Grid */}
      <section className="px-8 py-24 bg-slate-900 border-y border-slate-800">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-16">Platform Capabilities</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard icon={Search} title="Semantic Search" desc="Search your codebase by intent, not just keywords." />
            <FeatureCard icon={Building2} title="Architecture Analysis" desc="Auto-generate system design and architecture diagrams." />
            <FeatureCard icon={ShieldAlert} title="AI Code Review" desc="Automated scorecards for quality, security, and performance." />
            <FeatureCard icon={GitBranch} title="Impact Analysis" desc="Understand the blast radius of any code change." />
            <FeatureCard icon={Database} title="Dependency Mapping" desc="Visualize complex dependencies instantly." />
            <FeatureCard icon={LayoutDashboard} title="Repository Q&A" desc="Chat with your entire codebase like a senior engineer." />
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section className="px-8 py-24 max-w-5xl mx-auto text-center">
        <h2 className="text-3xl font-bold mb-16">How It Works</h2>
        <div className="flex flex-col md:flex-row items-center justify-between gap-8 relative z-0">
          <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-slate-800 -z-10" />
          <Step num="1" title="Upload Repository" desc="Provide a GitHub URL or ZIP file." />
          <Step num="2" title="CodeSense Indexes" desc="We parse, chunk, and embed source code." />
          <Step num="3" title="AI Understands" desc="LLMs process relationships and architecture." />
          <Step num="4" title="Start Exploring" desc="Search, ask, and analyze instantly." />
        </div>
      </section>

      {/* Footer / Stats */}
      <footer className="border-t border-slate-800 py-12 text-center text-slate-500 bg-slate-950">
        <div className="flex justify-center gap-12 mb-8 font-mono text-sm">
          <div><strong className="text-slate-300 text-lg block">10,000+</strong> Repositories Indexed</div>
          <div><strong className="text-slate-300 text-lg block">5M+</strong> Files Analyzed</div>
          <div><strong className="text-slate-300 text-lg block">50k+</strong> Questions Answered</div>
        </div>
        <p>© 2026 CodeSense. Premium AI Developer Platform.</p>
      </footer>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, desc }) {
  return (
    <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 hover:border-indigo-500/50 transition-colors text-left">
      <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center mb-4">
        <Icon size={20} className="text-indigo-400" />
      </div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-slate-400 leading-relaxed">{desc}</p>
    </div>
  );
}

function Step({ num, title, desc }) {
  return (
    <div className="flex flex-col items-center bg-slate-950 p-6 rounded-2xl border border-slate-800 w-full md:w-56 shadow-xl">
      <div className="w-12 h-12 rounded-full bg-indigo-600 flex items-center justify-center text-xl text-white font-bold mb-4 shadow-glow">
        {num}
      </div>
      <h4 className="font-semibold mb-2 text-slate-50">{title}</h4>
      <p className="text-sm text-slate-400">{desc}</p>
    </div>
  );
}
