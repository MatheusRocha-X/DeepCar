/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ["192.168.15.27", "127.0.0.1", "localhost"],
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com" },
      // OLX
      { protocol: "https", hostname: "img.olx.com.br" },
      { protocol: "https", hostname: "**.olx.com.br" },
      { protocol: "https", hostname: "**.olxcdn.com" },
      // Webmotors
      { protocol: "https", hostname: "**.webmotors.com.br" },
      { protocol: "https", hostname: "img.webmotors.com.br" },
      // iCarros
      { protocol: "https", hostname: "**.icarros.com.br" },
      { protocol: "https", hostname: "**.icarros.com" },
      // NaPista
      { protocol: "https", hostname: "**.napista.com.br" },
      // CDNs commonly used by these portals
      { protocol: "https", hostname: "**.cloudfront.net" },
      { protocol: "https", hostname: "**.cloudinary.com" },
      { protocol: "https", hostname: "**.amazonaws.com" },
      { protocol: "http", hostname: "localhost" },
    ],
    formats: ["image/avif", "image/webp"],
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "framer-motion"],
  },
};

module.exports = nextConfig;
