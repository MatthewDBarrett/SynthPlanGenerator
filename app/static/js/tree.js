(function () {
  const CARD_W = 170;
  const CARD_H = 56;
  const COL_GAP = 230;
  const ROW_GAP = 90;
  const SVG_NS = "http://www.w3.org/2000/svg";

  const container = document.getElementById("tree-container");
  const rootId = container.dataset.rootId;

  const state = { scale: 1, x: 0, y: 0 };

  function maxAncestorDepth(node, depth) {
    if (!node) return depth - 1;
    return Math.max(
      maxAncestorDepth(node.father || null, depth + 1),
      maxAncestorDepth(node.mother || null, depth + 1)
    );
  }

  function layoutAncestors(node, depth, slotIndex, totalHeight, maxDepth, positions, links, childPos) {
    if (!node || depth > maxDepth) return;
    const slotsAtDepth = Math.pow(2, depth);
    const slotWidth = totalHeight / slotsAtDepth;
    const y = slotIndex * slotWidth + slotWidth / 2;
    const x = -depth * COL_GAP;
    const pos = { node, x, y, depth };
    positions.push(pos);
    if (childPos) {
      links.push({ from: pos, to: childPos, kind: "parent" });
    }
    layoutAncestors(node.father || null, depth + 1, slotIndex * 2, totalHeight, maxDepth, positions, links, pos);
    layoutAncestors(node.mother || null, depth + 1, slotIndex * 2 + 1, totalHeight, maxDepth, positions, links, pos);
  }

  function measureDescendantHeight(node) {
    const children = node.children || [];
    if (!children.length) return 1;
    return children.reduce((sum, c) => sum + measureDescendantHeight(c), 0);
  }

  function layoutDescendants(node, depth, yOffset, positions, links, parentPos) {
    const h = measureDescendantHeight(node);
    const y = (yOffset + h / 2) * ROW_GAP;
    const x = depth * COL_GAP;
    const pos = { node, x, y, depth };
    positions.push(pos);
    if (parentPos) {
      links.push({ from: parentPos, to: pos, kind: "child" });
    }
    let cy = yOffset;
    (node.children || []).forEach((child) => {
      const ch = measureDescendantHeight(child);
      layoutDescendants(child, depth + 1, cy, positions, links, pos);
      cy += ch;
    });
    return y;
  }

  function buildLayout(root) {
    const positions = [];
    const links = [];

    const descHeight = measureDescendantHeight(root);
    const rootY = (descHeight / 2) * ROW_GAP;
    const rootPos = { node: root, x: 0, y: rootY, depth: 0, isRoot: true };
    positions.push(rootPos);

    let cy = 0;
    (root.children || []).forEach((child) => {
      const ch = measureDescendantHeight(child);
      layoutDescendants(child, 1, cy, positions, links, rootPos);
      cy += ch;
    });

    const ancestorDepth = Math.max(1, maxAncestorDepth(root, 0));
    const totalHeight = ROW_GAP * Math.pow(2, ancestorDepth);
    const ancestorPositions = [];
    const ancestorLinks = [];
    layoutAncestors(root.father || null, 1, 0, totalHeight, ancestorDepth, ancestorPositions, ancestorLinks, rootPos);
    layoutAncestors(root.mother || null, 1, 1, totalHeight, ancestorDepth, ancestorPositions, ancestorLinks, rootPos);

    const yShift = rootY - totalHeight / 2;
    ancestorPositions.forEach((p) => (p.y += yShift));

    positions.push(...ancestorPositions);
    links.push(...ancestorLinks);

    // spouses stack immediately below the root card
    const spouses = root.spouses || [];
    const spousePositions = spouses.map((sp, i) => ({
      node: sp,
      x: 0,
      y: rootY + (i + 1) * (CARD_H + 16),
      depth: 0,
      isSpouse: true,
    }));
    spousePositions.forEach((sp) => links.push({ from: rootPos, to: sp, kind: "spouse" }));
    positions.push(...spousePositions);

    return { positions, links };
  }

  function el(tag, attrs, parent) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    if (parent) parent.appendChild(node);
    return node;
  }

  function sexClass(sex) {
    if (sex === "M") return "sex-m";
    if (sex === "F") return "sex-f";
    return "sex-u";
  }

  function renderNode(pos, layer) {
    const { node, x, y } = pos;
    const g = el("g", { class: "tree-node", transform: `translate(${x - CARD_W / 2}, ${y - CARD_H / 2})` }, layer);
    if (node.id) {
      g.classList.add("clickable");
      g.addEventListener("click", () => {
        window.location.href = `/tree/${node.id}`;
      });
    }
    el(
      "rect",
      {
        class: `person-card ${sexClass(node.sex)}${pos.isRoot ? " root-card" : ""}`,
        width: CARD_W,
        height: CARD_H,
        rx: 8,
      },
      g
    );
    const name = el("text", { class: "person-name", x: 10, y: 22 }, g);
    name.textContent = node.name && node.name.length > 22 ? node.name.slice(0, 21) + "…" : node.name || "Unknown";

    const dates = [node.birth_date, node.is_living ? "" : node.death_date].filter(Boolean).join(" – ");
    if (dates) {
      const dateText = el("text", { class: "person-dates", x: 10, y: 40 }, g);
      dateText.textContent = dates;
    }
    return g;
  }

  function renderLink(link, layer) {
    const midX = (link.from.x + link.to.x) / 2;
    let d;
    if (link.kind === "spouse") {
      d = `M ${link.from.x} ${link.from.y + CARD_H / 2} L ${link.to.x} ${link.to.y - CARD_H / 2}`;
    } else if (link.to.x < link.from.x) {
      // parent link: link.to is the ancestor (further left)
      d = `M ${link.from.x - CARD_W / 2} ${link.from.y} H ${midX} V ${link.to.y} H ${link.to.x + CARD_W / 2}`;
    } else {
      // child link
      d = `M ${link.from.x + CARD_W / 2} ${link.from.y} H ${midX} V ${link.to.y} H ${link.to.x - CARD_W / 2}`;
    }
    el("path", { class: `tree-link tree-link-${link.kind}`, d, fill: "none" }, layer);
  }

  function applyTransform(g) {
    g.setAttribute("transform", `translate(${state.x}, ${state.y}) scale(${state.scale})`);
  }

  function render(data) {
    container.innerHTML = "";
    const svg = el("svg", { class: "tree-svg", width: "100%", height: "100%" }, container);
    const viewport = el("g", { class: "tree-viewport" }, svg);
    const linkLayer = el("g", { class: "tree-links" }, viewport);
    const nodeLayer = el("g", { class: "tree-nodes" }, viewport);

    const { positions, links } = buildLayout(data);
    links.forEach((link) => renderLink(link, linkLayer));
    positions.forEach((pos) => renderNode(pos, nodeLayer));

    // center the viewport on the root card initially
    const rect = container.getBoundingClientRect();
    state.scale = 1;
    state.x = rect.width / 2 - 0;
    state.y = rect.height / 2;
    applyTransform(viewport);

    setupPanZoom(svg, viewport);
  }

  function setupPanZoom(svg, viewport) {
    let dragging = false;
    let lastX = 0;
    let lastY = 0;

    svg.addEventListener("mousedown", (e) => {
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      svg.classList.add("dragging");
    });
    window.addEventListener("mouseup", () => {
      dragging = false;
      svg.classList.remove("dragging");
    });
    window.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      state.x += e.clientX - lastX;
      state.y += e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      applyTransform(viewport);
    });
    svg.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.1 : 0.9;
        state.scale = Math.min(3, Math.max(0.2, state.scale * factor));
        applyTransform(viewport);
      },
      { passive: false }
    );

    // touch support
    let touchStartDist = null;
    svg.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) {
        dragging = true;
        lastX = e.touches[0].clientX;
        lastY = e.touches[0].clientY;
      } else if (e.touches.length === 2) {
        touchStartDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
      }
    });
    svg.addEventListener("touchmove", (e) => {
      if (e.touches.length === 1 && dragging) {
        state.x += e.touches[0].clientX - lastX;
        state.y += e.touches[0].clientY - lastY;
        lastX = e.touches[0].clientX;
        lastY = e.touches[0].clientY;
        applyTransform(viewport);
      } else if (e.touches.length === 2 && touchStartDist) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        state.scale = Math.min(3, Math.max(0.2, state.scale * (dist / touchStartDist)));
        touchStartDist = dist;
        applyTransform(viewport);
      }
    });
    svg.addEventListener("touchend", () => {
      dragging = false;
      touchStartDist = null;
    });

    document.getElementById("zoom-in").addEventListener("click", () => {
      state.scale = Math.min(3, state.scale * 1.2);
      applyTransform(viewport);
    });
    document.getElementById("zoom-out").addEventListener("click", () => {
      state.scale = Math.max(0.2, state.scale * 0.8);
      applyTransform(viewport);
    });
    document.getElementById("zoom-reset").addEventListener("click", () => {
      const rect = svg.getBoundingClientRect();
      state.scale = 1;
      state.x = rect.width / 2;
      state.y = rect.height / 2;
      applyTransform(viewport);
    });
  }

  fetch(`/tree/${rootId}/data`)
    .then((res) => res.json())
    .then(render);
})();
