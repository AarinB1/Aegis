from __future__ import annotations

import streamlit.components.v1 as components


def render_sidebar_toggle_bridge() -> None:
    components.html(
        """
        <script>
        (function () {
          const doc = window.parent.document;
          const parentWindow = window.parent;
          const bridgeId = "aegis-sidebar-toggle-bridge";

          function openSidebar() {
            const expandButton = doc.querySelector('[data-testid="stExpandSidebarButton"]');
            if (expandButton) {
              expandButton.click();
              expandButton.dispatchEvent(new parentWindow.MouseEvent("click", { bubbles: true, cancelable: true, view: parentWindow }));
              expandButton.dispatchEvent(new parentWindow.PointerEvent("pointerdown", { bubbles: true }));
              expandButton.dispatchEvent(new parentWindow.PointerEvent("pointerup", { bubbles: true }));
              expandButton.dispatchEvent(new parentWindow.MouseEvent("mouseup", { bubbles: true }));
              return;
            }
            const collapsedButton = doc.querySelector('[data-testid="collapsedControl"] button');
            if (collapsedButton) {
              collapsedButton.click();
              collapsedButton.dispatchEvent(new parentWindow.MouseEvent("click", { bubbles: true, cancelable: true, view: parentWindow }));
            }
          }

          function ensureButton() {
            let button = doc.getElementById(bridgeId);
            if (!button) {
              button = doc.createElement("button");
              button.id = bridgeId;
              button.type = "button";
              button.textContent = "MENU";
              button.setAttribute("aria-label", "Open navigation");
              button.style.position = "fixed";
              button.style.top = "14px";
              button.style.left = "14px";
              button.style.zIndex = "10000";
              button.style.display = "none";
              button.style.alignItems = "center";
              button.style.justifyContent = "center";
              button.style.padding = "0.5rem 0.78rem";
              button.style.borderRadius = "999px";
              button.style.border = "1px solid #E8E4D8";
              button.style.background = "rgba(250, 250, 246, 0.96)";
              button.style.boxShadow = "0 16px 48px rgba(32, 24, 8, 0.12)";
              button.style.color = "#B8820F";
              button.style.fontFamily = "'JetBrains Mono', monospace";
              button.style.fontSize = "11px";
              button.style.letterSpacing = "0.14em";
              button.style.textTransform = "uppercase";
              button.style.cursor = "pointer";
              doc.body.appendChild(button);
            }
            button.onclick = openSidebar;
            return button;
          }

          function syncButton() {
            const button = ensureButton();
            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
            const expandButton = doc.querySelector('[data-testid="stExpandSidebarButton"]');
            const isCollapsed = sidebar && sidebar.getAttribute("aria-expanded") === "false";
            button.style.display = isCollapsed || !!expandButton ? "inline-flex" : "none";
          }

          syncButton();
          window.setInterval(syncButton, 400);
        })();
        </script>
        """,
        height=0,
        width=0,
    )
