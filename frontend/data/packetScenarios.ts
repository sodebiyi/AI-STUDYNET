export interface PacketStage {
  id: string;
  title: string;
  location: string;
  layer: "Application" | "Transport (TCP/UDP)" | "Network (IP)" | "Data Link (Ethernet)" | "Physical";
  description: string;
  headers?: [string, string][];
}

export interface PacketScenario {
  id: string;
  label: string;
  description: string;
  stages: PacketStage[];
}

const DNS_QUERY_HEADERS: [string, string][] = [
  ["Query", "example.com"],
  ["Record Type", "A"],
  ["Server", "8.8.8.8 (resolver)"],
  ["Transaction ID", "0x4a2f"],
];

const DNS_RESPONSE_HEADERS: [string, string][] = [
  ["Query", "example.com"],
  ["Response", "93.184.216.34"],
  ["Record Type", "A"],
  ["TTL", "300s"],
];

const ARP_HEADERS: [string, string][] = [
  ["Sender IP", "192.168.1.10"],
  ["Sender MAC", "AA:BB:CC:00:00:01"],
  ["Target IP", "192.168.1.1 (default gateway)"],
  ["Opcode", "Request → Reply"],
];

const ETHERNET_HEADERS: [string, string][] = [
  ["Source MAC", "AA:BB:CC:00:00:01"],
  ["Destination MAC", "AA:BB:CC:00:00:FE (gateway)"],
  ["EtherType", "0x0800 (IPv4)"],
];

const IPV4_HEADERS: [string, string][] = [
  ["Source IP", "192.168.1.10"],
  ["Destination IP", "93.184.216.34"],
  ["TTL", "64"],
  ["Protocol", "6 (TCP)"],
];

const TCP_SYN_HEADERS: [string, string][] = [
  ["Source Port", "51342"],
  ["Destination Port", "443"],
  ["Sequence Number", "1000000"],
  ["Flags", "SYN"],
];

const TCP_SYNACK_HEADERS: [string, string][] = [
  ["Source Port", "443"],
  ["Destination Port", "51342"],
  ["Sequence Number", "5000000"],
  ["Acknowledgement Number", "1000001"],
  ["Flags", "SYN, ACK"],
];

const TCP_ACK_HEADERS: [string, string][] = [
  ["Source Port", "51342"],
  ["Destination Port", "443"],
  ["Acknowledgement Number", "5000001"],
  ["Flags", "ACK"],
];

const TLS_HELLO_HEADERS: [string, string][] = [
  ["TLS Version", "TLS 1.3"],
  ["SNI", "example.com"],
  ["Cipher Suites", "TLS_AES_128_GCM_SHA256, …"],
];

const HTTP_REQUEST_HEADERS: [string, string][] = [
  ["Method", "GET /"],
  ["Host", "example.com"],
  ["User-Agent", "Mozilla/5.0"],
  ["Accept", "text/html"],
];

const NAT_HEADERS: [string, string][] = [
  ["Inside Local", "192.168.1.10:51342"],
  ["Inside Global", "203.0.113.5:40021"],
  ["Translation Type", "PAT (overload)"],
];

const ICMP_ECHO_HEADERS: [string, string][] = [
  ["Type", "8 (Echo Request)"],
  ["Source IP", "192.168.1.10"],
  ["Destination IP", "192.168.1.20"],
  ["Sequence", "1"],
];

const ICMP_REPLY_HEADERS: [string, string][] = [
  ["Type", "0 (Echo Reply)"],
  ["Source IP", "192.168.1.20"],
  ["Destination IP", "192.168.1.10"],
  ["Sequence", "1"],
];

export const PACKET_SCENARIOS: PacketScenario[] = [
  {
    id: "https",
    label: "Open https://example.com",
    description: "The full journey of an HTTPS request: DNS, ARP, TCP handshake, TLS, HTTP, NAT, and the response.",
    stages: [
      {
        id: "app-request",
        title: "Browser requests the page",
        location: "Application / Browser",
        layer: "Application",
        description: "You type https://example.com. The browser checks its cache — no cached IP, so it needs DNS resolution first.",
      },
      {
        id: "dns-query",
        title: "DNS query sent",
        location: "Operating System → DNS Resolver",
        layer: "Transport (TCP/UDP)",
        description: "The OS's resolver sends a UDP DNS query (port 53) asking 'what is the IP address of example.com?'",
        headers: DNS_QUERY_HEADERS,
      },
      {
        id: "dns-response",
        title: "DNS response received",
        location: "DNS Server → Operating System",
        layer: "Transport (TCP/UDP)",
        description: "The DNS server replies with the IP address for example.com, which the OS caches for future use.",
        headers: DNS_RESPONSE_HEADERS,
      },
      {
        id: "arp",
        title: "ARP resolves the default gateway",
        location: "NIC / Local Network",
        layer: "Data Link (Ethernet)",
        description: "The destination is off-subnet, so the PC needs the MAC address of its default gateway before it can send anything. It broadcasts an ARP request.",
        headers: ARP_HEADERS,
      },
      {
        id: "ethernet",
        title: "Ethernet frame built",
        location: "NIC",
        layer: "Data Link (Ethernet)",
        description: "The NIC wraps the outgoing IP packet in an Ethernet frame addressed to the gateway's MAC address (not the server's — that's what routing is for).",
        headers: ETHERNET_HEADERS,
      },
      {
        id: "ip-packet",
        title: "IP packet built",
        location: "Operating System (IP stack)",
        layer: "Network (IP)",
        description: "The OS builds an IP packet with the PC's own IP as source and the web server's IP as destination.",
        headers: IPV4_HEADERS,
      },
      {
        id: "tcp-syn",
        title: "TCP handshake: SYN",
        location: "Operating System → Router → Internet",
        layer: "Transport (TCP/UDP)",
        description: "Before any data is sent, TCP establishes a connection. The client sends a SYN segment to the server's port 443.",
        headers: TCP_SYN_HEADERS,
      },
      {
        id: "tcp-synack",
        title: "TCP handshake: SYN-ACK",
        location: "Web Server → Client",
        layer: "Transport (TCP/UDP)",
        description: "The server acknowledges and sends its own SYN back.",
        headers: TCP_SYNACK_HEADERS,
      },
      {
        id: "tcp-ack",
        title: "TCP handshake: ACK",
        location: "Client → Web Server",
        layer: "Transport (TCP/UDP)",
        description: "The client acknowledges the server's SYN. The connection is now established.",
        headers: TCP_ACK_HEADERS,
      },
      {
        id: "tls-hello",
        title: "TLS handshake begins",
        location: "Client ↔ Web Server",
        layer: "Application",
        description: "Since this is HTTPS, a TLS handshake negotiates encryption before any HTTP data is exchanged.",
        headers: TLS_HELLO_HEADERS,
      },
      {
        id: "nat",
        title: "Router performs NAT",
        location: "Router / Firewall",
        layer: "Network (IP)",
        description: "The home/office router translates the PC's private IP to its own public IP (PAT) before forwarding onto the Internet.",
        headers: NAT_HEADERS,
      },
      {
        id: "http-request",
        title: "HTTP request sent (encrypted)",
        location: "Client → Web Server",
        layer: "Application",
        description: "Inside the encrypted TLS tunnel, the browser sends its HTTP GET request.",
        headers: HTTP_REQUEST_HEADERS,
      },
      {
        id: "server-response",
        title: "Server responds",
        location: "Web Server → Client",
        layer: "Application",
        description: "The web server processes the request and sends back the HTML page, still encrypted, retracing the path in reverse.",
      },
      {
        id: "render",
        title: "Browser renders the page",
        location: "Application / Browser",
        layer: "Application",
        description: "The browser receives the response and renders the page for you.",
      },
    ],
  },
  {
    id: "dns",
    label: "Resolve a DNS name",
    description: "Just the DNS resolution process in isolation — useful for understanding recursive vs. cached lookups.",
    stages: [
      {
        id: "app-lookup",
        title: "Application needs a name resolved",
        location: "Application",
        layer: "Application",
        description: "An application (browser, ping, curl…) needs to turn a hostname into an IP address before it can open a connection.",
      },
      {
        id: "os-cache",
        title: "OS checks its resolver cache",
        location: "Operating System",
        layer: "Application",
        description: "The OS first checks whether it already knows the answer. If not, it queries the configured DNS server.",
      },
      {
        id: "dns-query",
        title: "DNS query sent (UDP/53)",
        location: "Operating System → DNS Resolver",
        layer: "Transport (TCP/UDP)",
        description: "A UDP datagram is sent to the configured DNS server (often the router, an ISP resolver, or a public resolver like 8.8.8.8).",
        headers: DNS_QUERY_HEADERS,
      },
      {
        id: "dns-response",
        title: "DNS response received",
        location: "DNS Server → Operating System",
        layer: "Transport (TCP/UDP)",
        description: "The resolver returns the IP address (or an error, e.g. NXDOMAIN, if the name doesn't exist) with a TTL telling the OS how long it can cache the answer.",
        headers: DNS_RESPONSE_HEADERS,
      },
      {
        id: "app-continues",
        title: "Application continues",
        location: "Application",
        layer: "Application",
        description: "Now that it has an IP address, the application can proceed to open a TCP or UDP connection to it.",
      },
    ],
  },
  {
    id: "ping",
    label: "Ping another PC",
    description: "A simple ICMP echo request/reply between two hosts on the same local network.",
    stages: [
      {
        id: "app-ping",
        title: "ping command issued",
        location: "Application / Shell",
        layer: "Application",
        description: "The user runs 'ping 192.168.1.20'. No DNS lookup is needed since the destination is already an IP address.",
      },
      {
        id: "arp",
        title: "ARP resolves the destination MAC",
        location: "NIC / Local Network",
        layer: "Data Link (Ethernet)",
        description: "Since the destination is on the same subnet, the PC needs its MAC address (not a gateway's). It broadcasts an ARP request if it doesn't already have one cached.",
        headers: ARP_HEADERS,
      },
      {
        id: "icmp-echo",
        title: "ICMP Echo Request sent",
        location: "Operating System (ICMP)",
        layer: "Network (IP)",
        description: "The OS builds an ICMP Echo Request packet — there's no TCP/UDP segment involved, ICMP rides directly on IP.",
        headers: ICMP_ECHO_HEADERS,
      },
      {
        id: "ethernet",
        title: "Ethernet frame built and sent",
        location: "NIC → Switch",
        layer: "Data Link (Ethernet)",
        description: "The ICMP packet is wrapped in an Ethernet frame addressed directly to the destination PC's MAC address and sent out onto the wire.",
        headers: ETHERNET_HEADERS,
      },
      {
        id: "switch-forward",
        title: "Switch forwards the frame",
        location: "Switch",
        layer: "Data Link (Ethernet)",
        description: "The switch looks up the destination MAC in its MAC address table and forwards the frame only out the correct port (not a broadcast).",
      },
      {
        id: "icmp-reply",
        title: "ICMP Echo Reply sent back",
        location: "Destination PC → Source PC",
        layer: "Network (IP)",
        description: "The destination PC replies with an ICMP Echo Reply, retracing the path back to the source.",
        headers: ICMP_REPLY_HEADERS,
      },
      {
        id: "app-result",
        title: "ping reports the result",
        location: "Application / Shell",
        layer: "Application",
        description: "The shell displays round-trip time and success/failure for each echo — or 'Request timed out' if no reply arrived.",
      },
    ],
  },
];
