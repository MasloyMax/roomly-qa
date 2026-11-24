import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize(
    "width",
    [
        pytest.param(320, id="mobile-320"),
        pytest.param(820, id="single-column-820"),
        pytest.param(
            821,
            id="two-columns-821",
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-06: на ширине 821 px обрезается заголовок",
                raises=AssertionError,
            ),
        ),
    ],
)
def test_heading_is_not_clipped(page: Page, base_url: str, width: int) -> None:
    page.set_viewport_size({"width": width, "height": 805})
    response = page.goto(base_url, wait_until="domcontentloaded")
    if response is None or not response.ok:
        raise RuntimeError("Roomly did not load successfully")
    heading = page.get_by_role("heading", level=1)
    heading.wait_for(state="visible")
    page.wait_for_function("document.fonts.status === 'loaded'")

    geometry = heading.evaluate("""heading => {
      const fonts = [...document.fonts];
      const clips = [];
      for (let ancestor = heading.parentElement; ancestor; ancestor = ancestor.parentElement) {
        const style = getComputedStyle(ancestor);
        const rect = ancestor.getBoundingClientRect();
        clips.push({
          x: /^(hidden|clip|auto|scroll)$/.test(style.overflowX),
          y: /^(hidden|clip|auto|scroll)$/.test(style.overflowY),
          left: rect.left + ancestor.clientLeft,
          right: rect.left + ancestor.clientLeft + ancestor.clientWidth,
          top: rect.top + ancestor.clientTop,
          bottom: rect.top + ancestor.clientTop + ancestor.clientHeight
        });
      }
      const clipped = [];
      const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT);
      let characters = 0;
      let node;
      while ((node = walker.nextNode())) {
        for (let index = 0; index < node.length; index++) {
          if (!node.textContent[index].trim()) continue;
          const range = document.createRange();
          range.setStart(node, index);
          range.setEnd(node, index + 1);
          const rect = range.getBoundingClientRect();
          if (!rect.width || !rect.height) continue;
          characters++;
          if (clips.some(clip =>
            (clip.x && (rect.left < clip.left - 1 || rect.right > clip.right + 1)) ||
            (clip.y && (rect.top < clip.top - 1 || rect.bottom > clip.bottom + 1)))) {
            clipped.push({character: node.textContent[index], left: rect.left, right: rect.right});
          }
        }
      }
      return {
        text: heading.innerText,
        characters,
        loadedFonts: fonts.filter(font => font.status === 'loaded').length,
        failedFonts: fonts.filter(font => font.status === 'error').length,
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: innerWidth,
        clipped
      };
    }""")
    if (
        "Забронируйте" not in geometry["text"]
        or not geometry["characters"]
        or not geometry["loadedFonts"]
        or geometry["failedFonts"]
        or geometry["viewportWidth"] != width
    ):
        raise RuntimeError(f"Heading or fonts are not ready for a layout check: {geometry}")

    if geometry["documentWidth"] > width:
        raise RuntimeError(f"Unexpected horizontal page overflow at {width} px: {geometry}")
    assert not geometry["clipped"], f"Heading text is clipped at {width} px: {geometry['clipped']}"
