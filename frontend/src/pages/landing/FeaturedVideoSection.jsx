import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Link } from 'react-router-dom';

export default function FeaturedVideoSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="bg-black pt-6 md:pt-10 pb-20 md:pb-32 px-6 overflow-hidden flex justify-center">
      <motion.div 
        ref={ref}
        initial={{ opacity: 0, y: 60 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 60 }}
        transition={{ duration: 0.9 }}
        className="w-full max-w-6xl rounded-3xl overflow-hidden aspect-video relative"
      >
        <video 
          className="w-full h-full object-cover"
          muted autoPlay loop playsInline preload="auto"
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260402_054547_9875cfc5-155a-4229-8ec8-b7ba7125cbf8.mp4"
        />
        
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />
        
        <div className="absolute bottom-0 left-0 right-0 p-6 md:p-10 flex flex-col md:flex-row items-end justify-between gap-6">
          <div className="liquid-glass rounded-2xl p-6 md:p-8 max-w-md w-full md:w-auto">
            <h3 className="text-white/50 text-xs tracking-widest uppercase mb-3">Our Approach</h3>
            <p className="text-white text-sm md:text-base leading-relaxed">
              We believe in the power of AI-driven exploration. Every codebase starts with a structure, and every answer opens a new door to innovation.
            </p>
          </div>
          
          <Link to="/dashboard">
            <motion.button 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="liquid-glass rounded-full px-8 py-3 text-white text-sm font-medium w-full md:w-auto whitespace-nowrap"
            >
              Explore more
            </motion.button>
          </Link>
        </div>
      </motion.div>
    </section>
  );
}
