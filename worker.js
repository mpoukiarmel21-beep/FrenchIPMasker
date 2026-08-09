// Cloudflare Worker - French IP Proxy
// Deployed on CF's Paris edge. Provides clean CF IPs for fallback.
// Handles both HTTP forwarding and IP health checks.

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Health check / IP display
    if (path === "/" || path === "/ip") {
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      const country = request.cf?.country || "FR";
      const colo = request.cf?.colo || "CDG";
      const info = {
        ip: ip,
        country: country,
        colo: colo,
        city: request.cf?.city || "Paris",
        asn: request.cf?.asn || "",
        status: "ok",
        provider: "Cloudflare Paris"
      };
      return new Response(JSON.stringify(info, null, 2), {
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
      });
    }

    // Forward proxy: /fetch?url=TARGET_URL
    if (path === "/fetch") {
      const target = url.searchParams.get("url");
      if (!target) {
        return new Response(JSON.stringify({ error: "Missing ?url= parameter" }), {
          status: 400,
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
        });
      }

      try {
        // Decode URL if needed
        let targetUrl = target;
        if (!target.startsWith("http")) {
          targetUrl = decodeURIComponent(target);
        }

        const targetResp = await fetch(targetUrl, {
          method: request.method,
          headers: {
            "User-Agent": request.headers.get("User-Agent") || "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": request.headers.get("Accept") || "*/*",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate"
          },
          redirect: "follow"
        });

        // Build response
        const respHeaders = new Headers();
        respHeaders.set("Access-Control-Allow-Origin", "*");
        respHeaders.set("X-Proxied-By", "FrenchIPMasker-CF");
        respHeaders.set("X-Proxy-IP", request.headers.get("CF-Connecting-IP") || "cf");

        // Forward content-type if available
        const ct = targetResp.headers.get("Content-Type");
        if (ct) respHeaders.set("Content-Type", ct);

        return new Response(targetResp.body, {
          status: targetResp.status,
          headers: respHeaders
        });

      } catch (e) {
        return new Response(JSON.stringify({ error: "Fetch failed", detail: e.message }), {
          status: 502,
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
        });
      }
    }

    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "*"
        }
      });
    }

    // Default: show IP
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    return new Response(JSON.stringify({
      ip: ip,
      country: request.cf?.country || "FR",
      colo: request.cf?.colo || "CDG",
      status: "ok"
    }), {
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
    });
  }
};
