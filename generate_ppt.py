import os
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def add_run(p, text, bold=False, size=Pt(10), color=None, font_name='Segoe UI'):
    r = p.add_run()
    r.text = text
    r.font.name = font_name
    r.font.bold = bold
    r.font.size = size
    if color:
        r.font.color.rgb = color
    return r

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Theme colors
    BG_DARK = RGBColor(11, 19, 43)        # #0B132B Deep Space
    PANEL_DARK = RGBColor(23, 37, 68)     # #172544 Navy Card
    PANEL_BORDER = RGBColor(46, 74, 110)  # #2E4A6E Border
    CYAN_ACCENT = RGBColor(56, 189, 248)  # #38BDF8 Cyan
    CYAN_DARK = RGBColor(14, 165, 233)    # #0EA5E9 Blue
    GREEN_ACCENT = RGBColor(16, 185, 129) # #10B981 Emerald
    TEXT_LIGHT = RGBColor(248, 250, 252)  # #F8FAFC White
    TEXT_MUTED = RGBColor(148, 163, 184)  # #94A3B8 Muted
    CARD_BG = RGBColor(15, 23, 42)        # #0F172A Dark Slate

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_DARK
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category_text="WIREVIEW HTTP • PROTOCOL INSPECTOR"):
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        add_run(p_cat, category_text.upper(), bold=True, size=Pt(10), color=CYAN_ACCENT)

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.65))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        add_run(p_title, title_text, bold=True, size=Pt(22), color=TEXT_LIGHT)

    def add_card(slide, left, top, width, height, title="", border_color=PANEL_BORDER, bg_color=PANEL_DARK):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)
        if title:
            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_left = Inches(0.2)
            tf.margin_top = Inches(0.15)
            tf.margin_right = Inches(0.2)
            p = tf.paragraphs[0]
            add_run(p, title, bold=True, size=Pt(12), color=CYAN_ACCENT)
        return card

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s1)

    line = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(1.8), Inches(1.2), Inches(0.06))
    line.fill.solid()
    line.fill.fore_color.rgb = CYAN_ACCENT
    line.line.fill.background()

    tbox = s1.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(10.9), Inches(3.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    
    p = tf1.paragraphs[0]
    add_run(p, "WireView HTTP", bold=True, size=Pt(44), color=TEXT_LIGHT)

    p2 = tf1.add_paragraph()
    p2.space_before = Pt(8)
    add_run(p2, "Low-Level TCP Socket HTTP/1.1 Engine & Real-Time Protocol Inspector", bold=True, size=Pt(20), color=CYAN_ACCENT)

    p3 = tf1.add_paragraph()
    p3.space_before = Pt(6)
    add_run(p3, "A Scratch-Built, Zero-Framework Networking Engine with Full-Duplex Reactive Observability", size=Pt(13), color=TEXT_MUTED)

    mcard = add_card(s1, Inches(1.2), Inches(5.2), Inches(10.9), Inches(1.3), bg_color=CARD_BG)
    mtf = mcard.text_frame
    mtf.margin_left = Inches(0.3)
    mtf.margin_top = Inches(0.2)
    mp1 = mtf.paragraphs[0]
    add_run(mp1, "Computer Networks Mini-Project Presentation  |  Academic Year 2026", bold=True, size=Pt(12), color=GREEN_ACCENT)

    mp2 = mtf.add_paragraph()
    mp2.space_before = Pt(4)
    add_run(mp2, "Topics Covered: Raw Berkeley Sockets (AF_INET) • RFC 9112 Wire Framing • Multi-Threaded TCP • SVG Pipeline Studio", size=Pt(10.5), color=TEXT_MUTED)

    # =========================================================================
    # SLIDE 2: INTRODUCTION & PROBLEM STATEMENT
    # =========================================================================
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s2)
    add_header(s2, "1. Introduction & Problem Statement", "PROJECT MOTIVATION & SCOPE")

    c1 = add_card(s2, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2), "The Problem: The 'Black-Box' Abstraction")
    tf = c1.text_frame
    bullets1 = [
        ("Modern web development relies entirely on high-level frameworks", "Frameworks like Flask, Django, Express, and FastAPI hide all networking fundamentals."),
        ("Zero Visibility into Socket Mechanics", "Developers never see raw socket.recv(), OS socket buffers, or TCP 3-way handshakes."),
        ("Wire-Format Framing is Obscured", "CRLF delimiters (\\r\\n), byte counting, and chunked transfer boundaries remain unseen."),
        ("RFC Violations are Silently Swallowed", "Framing ambiguities that cause HTTP Request Smuggling (RFC 9112) are rarely understood."),
    ]
    for bold_t, norm_t in bullets1:
        p = tf.add_paragraph()
        p.space_before = Pt(10)
        add_run(p, f"• {bold_t}: ", bold=True, size=Pt(10.5), color=TEXT_LIGHT)
        add_run(p, norm_t, size=Pt(10), color=TEXT_MUTED)

    c2 = add_card(s2, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2), "The Solution: WireView HTTP & Studio")
    tf2 = c2.text_frame
    bullets2 = [
        ("Zero-Framework TCP Server", "Built strictly on Python's raw socket module; no http.server, asyncio, or external libraries."),
        ("Strict RFC 9112 Implementation", "Complete request parser, security validator, dynamic router, and byte-level serializer."),
        ("Microsecond Observability Bus", "Nanosecond instrumentation emits live events via Server-Sent Events (SSE)."),
        ("Live SVG Pipeline Visualizer", "A reactive UI traces each request sequentially through all 8 internal processing stages."),
    ]
    for bold_t, norm_t in bullets2:
        p = tf2.add_paragraph()
        p.space_before = Pt(10)
        add_run(p, f"✔ {bold_t}: ", bold=True, size=Pt(10.5), color=GREEN_ACCENT)
        add_run(p, norm_t, size=Pt(10), color=TEXT_MUTED)

    # =========================================================================
    # SLIDE 3: WORKING - 8-STAGE PROCESSING PIPELINE
    # =========================================================================
    s3 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s3)
    add_header(s3, "2. Working Process: The 8-Stage Architecture", "STEP-BY-STEP REQUEST LIFECYCLE")

    stages = [
        ("1. TCP Accept", "socket.accept()", "OS 3-way handshake established. Assigns connection ID & spawns worker thread."),
        ("2. StreamBuffer", "recv() + Chunk Scan", "Reads raw socket bytes (8KB chunks). Buffers across fragmentation to \\r\\n\\r\\n."),
        ("3. HTTP Parser", "RFC 9112 Wire Parser", "Extracts Request-Line (Method, URI, Version), decodes headers, measures Content-Length."),
        ("4. Validator", "RFC Framing Checks", "Enforces Host header, validates size limits (URI < 8KB), prevents traversal (/../)."),
        ("5. Router", "Pattern Dispatch", "Matches exact & param routes (/items/{id}). Emits RFC 405 with 'Allow' header if verb fails."),
        ("6. Handler", "Business Logic", "Executes REST CRUD controller, inspects JSON payloads, builds Response model."),
        ("7. Serializer", "Wire Byte Formatting", "Serializes Status-Line, headers (Date, Content-Length, Keep-Alive), CRLF, and body."),
        ("8. TCP Transmit", "sendall() to Socket", "Transmits byte stream over TCP. Records microsecond timings; re-arms socket for Keep-Alive.")
    ]

    card_w = Inches(2.7)
    card_h = Inches(2.4)
    for idx, (st_name, st_sub, st_desc) in enumerate(stages):
        row = idx // 4
        col = idx % 4
        x = Inches(0.8) + col * Inches(2.95)
        y = Inches(1.6) + row * Inches(2.65)
        
        card = add_card(s3, x, y, card_w, card_h, bg_color=CARD_BG, border_color=CYAN_DARK if idx < 4 else GREEN_ACCENT)
        ctf = card.text_frame
        ctf.margin_left = ctf.margin_top = ctf.margin_right = Inches(0.18)
        
        cp1 = ctf.paragraphs[0]
        add_run(cp1, st_name, bold=True, size=Pt(12), color=CYAN_ACCENT if idx < 4 else GREEN_ACCENT)
        
        cp2 = ctf.add_paragraph()
        cp2.space_before = Pt(2)
        add_run(cp2, st_sub, size=Pt(9), color=TEXT_LIGHT, font_name='Courier New')
        
        cp3 = ctf.add_paragraph()
        cp3.space_before = Pt(6)
        add_run(cp3, st_desc, size=Pt(9.5), color=TEXT_MUTED)

    # =========================================================================
    # SLIDE 4: DEVICES & TECHNOLOGIES USED
    # =========================================================================
    s4 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s4)
    add_header(s4, "3. Devices, Tools & Technology Stack", "SYSTEM SPECIFICATIONS & COMPONENTS")

    col_w = Inches(3.7)
    col_h = Inches(5.2)

    # Card 1: Core Socket Server
    c_srv = add_card(s4, Inches(0.8), Inches(1.6), col_w, col_h, "Core Socket Engine (Backend)", border_color=CYAN_ACCENT)
    stf = c_srv.text_frame
    srv_items = [
        ("Language", "Python 3.11+ (Standard Library)"),
        ("Socket API", "socket.socket(AF_INET, SOCK_STREAM)"),
        ("Concurrency", "Thread-pool worker model (32 threads)"),
        ("Protocols", "HTTP/1.1 (RFC 9112) & SSE (RFC 8895)"),
        ("Buffering", "StreamBuffer with circular chunk scan"),
        ("Routing", "Trie-based Regex & Exact Path Matching"),
        ("Security", "Safe path resolution & RFC header validation"),
    ]
    for label, val in srv_items:
        p = stf.add_paragraph()
        p.space_before = Pt(8)
        add_run(p, f"• {label}: ", bold=True, size=Pt(10), color=CYAN_ACCENT)
        add_run(p, val, size=Pt(9.5), color=TEXT_LIGHT)

    # Card 2: WireView Studio
    c_std = add_card(s4, Inches(4.8), Inches(1.6), col_w, col_h, "WireView Studio (Frontend)", border_color=GREEN_ACCENT)
    ctf = c_std.text_frame
    std_items = [
        ("Framework", "React 19 + TypeScript 5.0"),
        ("Build Tool", "Vite 8.3 (High-speed HMR bundle)"),
        ("Visualizer", "Declarative SVG Canvas with keyframe glow"),
        ("Styling", "Vanilla CSS, Cyberpunk Glassmorphism"),
        ("Streaming", "EventSource API (Server-Sent Events)"),
        ("Icons", "Lucide React (Feather design system)"),
        ("Telemetry UI", "Metrics Dashboard, Request Lab, Inspector"),
    ]
    for label, val in std_items:
        p = ctf.add_paragraph()
        p.space_before = Pt(8)
        add_run(p, f"• {label}: ", bold=True, size=Pt(10), color=GREEN_ACCENT)
        add_run(p, val, size=Pt(9.5), color=TEXT_LIGHT)

    # Card 3: Environment & Hardware
    c_env = add_card(s4, Inches(8.8), Inches(1.6), col_w, col_h, "Hardware & Diagnostics", border_color=CYAN_DARK)
    etf = c_env.text_frame
    env_items = [
        ("Host Machine", "x64 Workstation (16 GB RAM, NVMe SSD)"),
        ("Operating System", "Windows 11 / Linux Kernel 5.15+"),
        ("Loopback Adapter", "127.0.0.1:8080 (Sub-millisecond latency)"),
        ("Benchmarking", "cURL 8.0, PowerShell 7 Test-Harness"),
        ("Browser Client", "Chromium DevTools / Edge Inspector"),
        ("Test Suite", "Python unittest (50+ automated unit tests)"),
        ("Process Daemon", "Independent background service runner"),
    ]
    for label, val in env_items:
        p = etf.add_paragraph()
        p.space_before = Pt(8)
        add_run(p, f"• {label}: ", bold=True, size=Pt(10), color=CYAN_DARK)
        add_run(p, val, size=Pt(9.5), color=TEXT_LIGHT)

    # =========================================================================
    # SLIDE 5: SIMULATION SETUP & TEST SCENARIOS
    # =========================================================================
    s5 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s5)
    add_header(s5, "4. Simulation Setup & Educational Scenarios", "TEST MATRIX & PROTOCOL OBSERVATIONS")

    table_shape = s5.shapes.add_table(9, 5, Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.0))
    table = table_shape.table

    headers = ["Scenario", "HTTP Method & Route", "Payload / Conditions", "Expected Status", "Observed Traversal"]
    col_widths = [Inches(2.2), Inches(2.2), Inches(2.4), Inches(1.6), Inches(3.3)]
    for i, w in enumerate(col_widths):
        table.columns[i].width = w

    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = ""
        cell.fill.solid()
        cell.fill.fore_color.rgb = PANEL_DARK
        p = cell.text_frame.paragraphs[0]
        add_run(p, h, bold=True, size=Pt(10.5), color=CYAN_ACCENT)

    sim_rows = [
        ("Health Probe", "GET /health", "Empty header/body", "200 OK", "All 8 stages traverse in 360ms. Latency < 1ms."),
        ("Engine Capability", "GET /api/info", "Inspect server RFC limits", "200 OK", "Returns JSON feature flag & socket chunk buffer size."),
        ("REST Resource Creation", "POST /api/items", "JSON RFC metadata body", "201 Created", "Parser extracts Content-Length; handler stores in RAM."),
        ("Payload Echo", "POST /api/echo", "Arbitrary client payload", "200 OK", "Exact wire framing verification & body echo."),
        ("Unknown Route", "GET /api/unknown", "Non-existent URI pattern", "404 Not Found", "Router terminates flow; Handler skipped; error JSON."),
        ("Method Rejection", "POST /api/time", "POST to GET-only route", "405 Method Not Allowed", "Emits mandatory RFC 'Allow: GET, HEAD' header."),
        ("Simulated Fault", "GET /api/test/error", "Handler raises exception", "500 Internal Error", "Catches crash gracefully; worker thread survives."),
        ("Security Defense", "GET /../../etc/passwd", "Directory traversal probe", "400 / 404 Blocked", "Path sanitizer halts escape outside static root.")
    ]

    for r_idx, r_data in enumerate(sim_rows, start=1):
        bg_col = CARD_BG if r_idx % 2 == 1 else PANEL_DARK
        for c_idx, val in enumerate(r_data):
            cell = table.cell(r_idx, c_idx)
            cell.text = ""
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg_col
            p = cell.text_frame.paragraphs[0]
            val_col = GREEN_ACCENT if c_idx == 3 else TEXT_LIGHT
            add_run(p, val, size=Pt(9.5), color=val_col)

    # =========================================================================
    # SLIDE 6: LIVE DEMONSTRATION & SCREENSHOT
    # =========================================================================
    s6 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s6)
    add_header(s6, "5. Live Protocol Visualizer & Studio", "REAL-TIME SVG CANVAS & INTERACTIVE LAB")

    img_dash = Path(r"C:\Users\ayush\.gemini\antigravity-ide\brain\4c8efd47-86d2-4c12-ad26-adfaffa47915\get_health_animated_final_1791627802895.png")
    if img_dash.is_file():
        s6.shapes.add_picture(str(img_dash), Inches(0.8), Inches(1.5), width=Inches(8.5))

    right_c = add_card(s6, Inches(9.5), Inches(1.5), Inches(3.0), Inches(5.3), "Visualizer Features", border_color=CYAN_ACCENT)
    rtf = right_c.text_frame
    features = [
        ("Paced Step Animation", "Animates stages sequentially (360ms default) so humans can follow."),
        ("Active vs Completed", "Active node pulses cyan with dashed flow; completed nodes turn green."),
        ("Speed Controller", "User can switch between 0.5x Slow, 1x Normal, and 2x Fast."),
        ("Clean Request Stream", "Background metrics are isolated; only user-triggered requests light up."),
        ("Replay Trace Button", "Re-run the packet animation on demand with a single click.")
    ]
    for ft_title, ft_desc in features:
        p = rtf.add_paragraph()
        p.space_before = Pt(8)
        add_run(p, f"★ {ft_title}\n", bold=True, size=Pt(10), color=CYAN_ACCENT)
        add_run(p, ft_desc, size=Pt(9), color=TEXT_MUTED)

    # =========================================================================
    # SLIDE 7: METRICS & WIRE INSPECTION
    # =========================================================================
    s7 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s7)
    add_header(s7, "6. Observability: Metrics & Wire Inspection", "FULL-DUPLEX REAL-TIME TELEMETRY")

    img_metrics = Path(r"C:\Users\ayush\.gemini\antigravity-ide\brain\4c8efd47-86d2-4c12-ad26-adfaffa47915\metrics_tab_view_1791624793850.png")
    img_events = Path(r"C:\Users\ayush\.gemini\antigravity-ide\brain\4c8efd47-86d2-4c12-ad26-adfaffa47915\event_log_view_1791624763826.png")

    if img_metrics.is_file():
        s7.shapes.add_picture(str(img_metrics), Inches(0.8), Inches(1.6), width=Inches(5.7))
        cap1 = s7.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(5.7), Inches(0.8))
        add_run(cap1.text_frame.paragraphs[0], "Metrics Dashboard: Live P50/P95 latency percentiles, throughput, status categories & socket counts.", size=Pt(9.5), color=CYAN_ACCENT)

    if img_events.is_file():
        s7.shapes.add_picture(str(img_events), Inches(6.8), Inches(1.6), width=Inches(5.7))
        cap2 = s7.shapes.add_textbox(Inches(6.8), Inches(5.8), Inches(5.7), Inches(0.8))
        add_run(cap2.text_frame.paragraphs[0], "Real-Time Event Stream: Nanosecond Server-Sent Events showing socket handshakes, parsing & routing.", size=Pt(9.5), color=GREEN_ACCENT)

    # =========================================================================
    # SLIDE 8: KEY ENGINEERING CHALLENGES
    # =========================================================================
    s8 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s8)
    add_header(s8, "7. Key Technical Challenges & Solutions", "NETWORKING ENGINEERING HIGHLIGHTS")

    chal_w = Inches(5.6)
    chal_h = Inches(2.4)

    b1 = add_card(s8, Inches(0.8), Inches(1.6), chal_w, chal_h, "1. TCP Byte Fragmentation & Boundary Scans", border_color=CYAN_ACCENT)
    tf = b1.text_frame
    p = tf.add_paragraph()
    p.space_before = Pt(4)
    add_run(p, "Challenge: TCP is a byte stream, not a message protocol. Headers can split across packets.\nSolution: Implemented StreamBuffer that reads in 8KB chunks, inspects double CRLF (\\r\\n\\r\\n) boundaries without over-consuming payload bytes.", size=Pt(10), color=TEXT_MUTED)

    b2 = add_card(s8, Inches(6.8), Inches(1.6), chal_w, chal_h, "2. Sub-Millisecond Speed vs Visual Pacing", border_color=GREEN_ACCENT)
    tf = b2.text_frame
    p = tf.add_paragraph()
    p.space_before = Pt(4)
    add_run(p, "Challenge: On localhost, Python processes requests in < 0.3ms, snapping all nodes green simultaneously.\nSolution: Introduced state-driven sequential reveal pacing (360ms/stage) to clearly animate the active packet front and traversed history.", size=Pt(10), color=TEXT_MUTED)

    b3 = add_card(s8, Inches(0.8), Inches(4.3), chal_w, chal_h, "3. Internal Telemetry Feedback Loops", border_color=CYAN_DARK)
    tf = b3.text_frame
    p = tf.add_paragraph()
    p.space_before = Pt(4)
    add_run(p, "Challenge: Studio metrics polling (/api/metrics every 1.2s) created an infinite loop of SSE events.\nSolution: Filtered telemetry polling with X-Internal-Poll headers, preventing background telemetry from interrupting user test flows.", size=Pt(10), color=TEXT_MUTED)

    b4 = add_card(s8, Inches(6.8), Inches(4.3), chal_w, chal_h, "4. RFC 9112 Request Smuggling Prevention", border_color=CYAN_ACCENT)
    tf = b4.text_frame
    p = tf.add_paragraph()
    p.space_before = Pt(4)
    add_run(p, "Challenge: Malformed framing or duplicate Content-Length headers create HTTP desync vulnerabilities.\nSolution: Strict RFC 9112 validator rejects duplicate headers, enforces positive integers, and strictly validates Host headers.", size=Pt(10), color=TEXT_MUTED)

    # =========================================================================
    # SLIDE 9: CONCLUSION & LEARNING OUTCOMES
    # =========================================================================
    s9 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s9)
    add_header(s9, "8. Conclusion & Learning Outcomes", "SUMMARY OF PROJECT RESULTS")

    concl_card = add_card(s9, Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.2), "Key Takeaways & Educational Impact")
    ctf = concl_card.text_frame
    points = [
        ("Complete Mastery of Low-Level Socket Programming", 
         "Successfully proved that a fully functional, multi-threaded, RFC-compliant HTTP server can be built from raw Berkeley sockets without heavy third-party abstractions."),
        ("Deep Understanding of Protocol Framing (RFC 9112)", 
         "Acquired practical expertise in stream buffers, CRLF parsing, header case-insensitivity, keep-alive connection reuse, and HTTP status code semantics."),
        ("Full-Stack Decoupled Observability", 
         "Engineered an asynchronous Server-Sent Events (SSE) telemetry bus linking a multi-threaded Python TCP daemon to a reactive React & SVG frontend."),
        ("Benchmark Performance & Reliability", 
         "Delivers sub-millisecond request latencies (< 0.5 ms), handles 32 concurrent worker threads, incorporates directory traversal security defenses, and runs leak-free.")
    ]
    for title, desc in points:
        p = ctf.add_paragraph()
        p.space_before = Pt(12)
        add_run(p, f"✔ {title}\n", bold=True, size=Pt(11.5), color=GREEN_ACCENT)
        add_run(p, desc, size=Pt(10.5), color=TEXT_LIGHT)

    # =========================================================================
    # SLIDE 10: REFERENCES & Q&A
    # =========================================================================
    s10 = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(s10)
    add_header(s10, "9. References & Open Discussion", "DOCUMENTATION & ACKNOWLEDGMENTS")

    r_card = add_card(s10, Inches(0.8), Inches(1.6), Inches(7.5), Inches(5.2), "Key Academic & Technical References")
    rtf = r_card.text_frame
    refs_list = [
        "IETF RFC 9110: HTTP Semantics (Fielding, Nottingham, Reschke, 2022).",
        "IETF RFC 9112: HTTP/1.1 Message Syntax and Routing (Fielding, Reschke, 2022).",
        "IETF RFC 7230: Hypertext Transfer Protocol: Message Syntax and Routing.",
        "W. Richard Stevens: UNIX Network Programming, Vol 1: The Sockets Networking API.",
        "J. Kurose & K. Ross: Computer Networking: A Top-Down Approach (8th Edition).",
        "Python Software Foundation: socket & threading library official documentation.",
        "Mozilla Developer Network (MDN): Server-Sent Events (EventSource) specification."
    ]
    for ref in refs_list:
        p = rtf.add_paragraph()
        p.space_before = Pt(8)
        add_run(p, f"• {ref}", size=Pt(9.5), color=TEXT_MUTED)

    qa_card = add_card(s10, Inches(8.6), Inches(1.6), Inches(3.9), Inches(5.2), "Thank You!", border_color=CYAN_ACCENT)
    qtf = qa_card.text_frame
    qp1 = qtf.add_paragraph()
    qp1.space_before = Pt(20)
    add_run(qp1, "WireView HTTP", bold=True, size=Pt(18), color=CYAN_ACCENT)

    qp2 = qtf.add_paragraph()
    qp2.space_before = Pt(8)
    add_run(qp2, "Questions & Live Demonstration", size=Pt(13), color=TEXT_LIGHT)

    qp3 = qtf.add_paragraph()
    qp3.space_before = Pt(20)
    add_run(qp3, "Ready to demonstrate live socket inspection and SVG packet tracing on port 8080.", size=Pt(10), color=GREEN_ACCENT)

    output_path = Path("WireView_HTTP_Mini_Project_Presentation.pptx").resolve()
    prs.save(str(output_path))
    print(f"Presentation successfully saved to: {output_path}")

if __name__ == "__main__":
    create_presentation()
