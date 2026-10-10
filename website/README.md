# ENGRAMM landing page

The product landing page, live at <https://engramm.vercel.app>. It is a static site with no build
step: plain HTML, CSS and JavaScript. It replaces the earlier download page in `site/`.

## Layout

```
website/
  vercel.json          Vercel settings: serve public/, cache headers for images, security headers
  public/
    index.html         all sections: hero, story stack, mission, principles, demo, early access
    styles.css         every style, dark and monochrome; responsive breakpoints at 980px and 640px
    main.js            one animation loop: scroll story, draggable card stack, demo player, marquee
    favicon.svg        the E mark
    og.jpg             link preview image
    img/               photographs (WebP)
```

## Run it locally

```sh
python3 -m http.server 4173 -d website/public
# open http://localhost:4173
```

## Deploy

On Vercel, set the project's Root Directory to `website`. With no framework and no build
command, Vercel serves `public/` as `vercel.json` specifies. Once the project is connected to
this repository, Vercel builds the branch `website` as production: every push there goes live.
Pushes to other branches, `main` included, are not deployed.

## How the hero and the card stack work

- When you scroll, the full-screen photo shrinks into the front card of a 3D stack. While it
  moves, only transforms and a clip change. Once it rests, it switches to the real card size
  so the browser has less to composite.
- Once the cards rest, you can drag the stack with the mouse, or swipe it on a phone, to turn
  it in 3D. Releasing it hands the momentum to a soft spring that brings the cards back to
  their resting pose. Vertical swipes still scroll the page.
- The layout is measured on resize, never per frame. Styles are written only when a value
  changes.

## External resources

The page loads two things from third parties: the Geist and Newsreader fonts from Google
Fonts, and the Lenis smooth-scroll script from jsDelivr. If either fails, the page still works
(system fonts and native scrolling). For a privacy product it is worth hosting both here
instead, because embedding Google Fonts sends visitors' IP addresses to Google.
