import React, { useContext, useEffect, useRef } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { Zap, Globe, ArrowRight, Instagram, Twitter } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';

import AboutSection from './landing/AboutSection';
import FeaturedVideoSection from './landing/FeaturedVideoSection';
import PhilosophySection from './landing/PhilosophySection';
import ServicesSection from './landing/ServicesSection';

export default function LandingPage() {
  const { authenticated } = useContext(AuthContext);
  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleCanPlay = () => {
      video.play().catch(e => console.log("Video auto-play prevented:", e));
      let start;
      const duration = 500;
      const animateOpacity = (timestamp) => {
        if (!start) start = timestamp;
        const progress = Math.min((timestamp - start) / duration, 1);
        video.style.opacity = progress;
        if (progress < 1) requestAnimationFrame(animateOpacity);
      };
      requestAnimationFrame(animateOpacity);
    };

    const handleTimeUpdate = () => {
      if (video.duration && video.duration - video.currentTime <= 0.55) {
        let start;
        const duration = 500;
        const startOpacity = parseFloat(video.style.opacity || 1);
        const animateOpacityOut = (timestamp) => {
          if (!start) start = timestamp;
          const progress = Math.min((timestamp - start) / duration, 1);
          video.style.opacity = startOpacity * (1 - progress);
          if (progress < 1) requestAnimationFrame(animateOpacityOut);
        };
        requestAnimationFrame(animateOpacityOut);
      }
    };

    const handleEnded = () => {
      video.style.opacity = 0;
      setTimeout(() => {
        video.currentTime = 0;
        video.play().catch(e => console.log("Video auto-play prevented:", e));
        let start;
        const duration = 500;
        const animateOpacityIn = (timestamp) => {
          if (!start) start = timestamp;
          const progress = Math.min((timestamp - start) / duration, 1);
          video.style.opacity = progress;
          if (progress < 1) requestAnimationFrame(animateOpacityIn);
        };
        requestAnimationFrame(animateOpacityIn);
      }, 100);
    };

    video.addEventListener('canplay', handleCanPlay);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('canplay', handleCanPlay);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('ended', handleEnded);
    };
  }, []);

  if (authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="bg-black text-slate-50 font-sans selection:bg-indigo-500/30 w-full overflow-x-hidden">
      {/* SECTION 1 -- HERO */}
      <section className="min-h-screen overflow-hidden relative flex flex-col">
        {/* Background video */}
        <video 
          ref={videoRef}
          className="absolute inset-0 w-full h-full object-cover object-bottom"
          muted playsInline preload="auto"
          style={{ opacity: 0 }}
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260405_074625_a81f018a-956b-43fb-9aee-4d1508e30e6a.mp4"
        />

        {/* Navbar */}
        <nav className="relative z-20 px-6 py-6 w-full">
          <div className="liquid-glass rounded-full max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap size={24} className="text-white" />
              <span className="text-white font-semibold text-lg tracking-tight">CodeSense</span>
              <div className="hidden md:flex gap-8 ml-8">
                <a href="#features" className="text-white/80 hover:text-white text-sm font-medium transition-colors">Features</a>
                <a href="#about" className="text-white/80 hover:text-white text-sm font-medium transition-colors">About</a>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <Link to="/login" className="text-white text-sm font-medium hover:text-white/80 transition-colors">
                Sign In
              </Link>
              <Link to="/dashboard" className="liquid-glass rounded-full px-6 py-2 text-white text-sm font-medium hover:bg-white/5 transition-colors">
                Explore Demo
              </Link>
            </div>
          </div>
        </nav>

        {/* Hero content */}
        <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 py-12 text-center -translate-y-[20%]">
          <h1 className="text-7xl md:text-8xl lg:text-9xl text-white tracking-tight whitespace-nowrap mb-8">
            Understand it <em className="font-['Instrument_Serif'] italic">all</em>.
          </h1>
          
          <div className="max-w-xl w-full mb-6">
            <div className="liquid-glass rounded-full pl-6 pr-2 py-2 flex items-center gap-3">
              <input 
                type="text" 
                placeholder="Enter GitHub URL to explore..." 
                className="bg-transparent flex-1 outline-none border-none text-white placeholder:text-white/40 min-w-0"
              />
              <Link to="/upload" className="bg-white rounded-full p-3 text-black hover:bg-white/90 transition-colors shrink-0">
                <ArrowRight size={20} />
              </Link>
            </div>
          </div>
          
          <p className="text-white/80 text-sm leading-relaxed px-4 max-w-lg mx-auto mb-8">
            Semantic Search, Architecture Analysis, and AI Code Review in one platform. Upload your repository today and never miss a dependency.
          </p>
          
          <Link to="/login" className="liquid-glass rounded-full px-8 py-3 text-white text-sm font-medium hover:bg-white/5 transition-colors">
            Join Waitlist
          </Link>
        </div>

        {/* Social icons footer */}
        <div className="relative z-10 flex justify-center gap-4 pb-12 mt-auto">
          <a href="#" className="liquid-glass rounded-full p-4 text-white/80 hover:text-white hover:bg-white/5 transition-all">
            <Globe size={20} />
          </a>
          <a href="#" className="liquid-glass rounded-full p-4 text-white/80 hover:text-white hover:bg-white/5 transition-all">
            <Twitter size={20} />
          </a>
          <a href="#" className="liquid-glass rounded-full p-4 text-white/80 hover:text-white hover:bg-white/5 transition-all">
            <Instagram size={20} />
          </a>
        </div>
      </section>

      {/* Other Sections */}
      <div id="about">
        <AboutSection />
      </div>
      <FeaturedVideoSection />
      <PhilosophySection />
      <div id="features">
        <ServicesSection />
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800/30 py-12 text-center text-white/40 bg-black text-sm">
        <p>© 2026 CodeSense. Premium AI Developer Platform.</p>
      </footer>
    </div>
  );
}
