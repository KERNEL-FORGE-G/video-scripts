"""Décors 2D composés avec les packs Kenney — plus aucune image générée.

Le moteur prélève une fenêtre dans un espace-monde de 2048x1152. Ce script
fabrique une image-monde par décor en empilant de vraies couches de paysage
(ciel, montagnes, collines, sol), de vraies tuiles de jeu et de vrais éléments
d'interface — tout CC0 (Kenney), donc reproductible hors ligne et sans quota.

    python3 build/build_decors.py                 # les huit plaques
    python3 build/build_decors.py wide campus     # quelques-unes, pour itérer

Deux précautions viennent de la mesure des assets. Les fonds Kenney sont livrés
quasi blancs (luminance 204 à 240) : ce sont des calques à teinter, d'où la
teinte imposée à chaque décor. Et dans l'UI pack, seules les variantes sans
relief supportent un étirement dans les deux axes — les « depth » portent une
lèvre plus épaisse en bas et ne s'étirent que dans la largeur.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "assets" / "kenney"
OUT = ROOT / "keyframes"
ASSETS = ROOT / "assets"

WW, WH = 2048, 1152          # l'espace-monde du moteur

BE = K / "kenney_background-elements-remastered"
BEP = BE / "PNG" / "Default"
BEE = BE / "Backgrounds" / "Elements"
PL = K / "kenney_new-platformer-pack-1.1"
PLT = PL / "Sprites" / "Tiles" / "Double"
PLB = PL / "Sprites" / "Backgrounds" / "Double"
UI = K / "kenney_ui-pack" / "PNG"
SC = K / "kenney_shape-characters" / "PNG" / "Double"
EM = K / "kenney_emotes-pack" / "PNG" / "Pixel" / "Style 1"

NAVY, CYAN, ORANGE = (30, 58, 138), (56, 214, 255), (249, 130, 38)
_c = {}


# --------------------------------------------------------------- fabriques
def png(d, name):
    """PNG Kenney, toujours chargé en RGBA : beaucoup sont en mode palette."""
    k = ("p", str(d / name))
    if k not in _c:
        _c[k] = Image.open(d / name).convert("RGBA")
    return _c[k]


LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


def teinte(im, couleur, lum=1.0):
    """Aplat coloré qui garde le dessin : c'est ce qui rend les décors frères.

    On repart de la luminance du sprite, pas de ses RVB. Deux raisons mesurées :
    les fonds Kenney sont quasi blancs et une simple multiplication par deux
    écrête tout — c'est ce qui délavait le campus ; et les boutons de l'UI pack
    sont bleus à la base, donc multipliés en orange ils vireraient à l'olive.
    Normaliser par le pixel le plus clair rend la teinte fidèle dans les deux cas.

    La clé porte l'adresse du sprite source, et `id()` n'est garanti unique que
    tant que l'objet vit. `panneau` teintait des images temporaires que le
    ramasse-miettes recyclait ensuite : une clé plus tardive retombait sur une
    entrée morte et renvoyait le dessin d'un autre. Le fanion du pylône est
    ainsi devenu une lamelle de 16×121 invisible. Une entrée garde donc sa
    source vivante, ce qui rend son adresse définitivement inusable.
    """
    k = ("t", id(im), couleur, round(lum, 3))
    hit = _c.get(k)
    if hit is not None:
        return hit[1]
    a = np.asarray(im, np.float32)
    l = a[..., :3] @ LUM
    plein = l[a[..., 3] > 8]
    ref = max(float(plein.max()) if plein.size else 255.0, 1.0)
    rgb = np.clip(l[..., None] / ref * np.array(couleur, np.float32) * lum, 0, 255)
    _c[k] = (im, Image.fromarray(np.dstack([rgb, a[..., 3]]).astype("uint8"), "RGBA"))
    return _c[k][1]


def rhen(im, h):
    k = ("r", id(im), int(h))
    hit = _c.get(k)
    if hit is not None:
        return hit[1]
    _c[k] = (im, im.resize((max(1, round(im.width * h / im.height)), int(h)),
                           Image.LANCZOS))
    return _c[k][1]


def panneau(couleur, w, h, style="border", pack="Blue"):
    """Neuf tranches d'un sprite de l'UI pack.

    Le pack ne contient aucun panneau ni aucune fenêtre : le plus grand
    rectangle disponible est un bouton de 384x128, avec des coins de 12 px.
    Étiré en neuf tranches, il devient ce qu'on veut.
    """
    w, h = max(28, int(w)), max(28, int(h))
    k = ("pan", couleur, w, h, style, pack)
    if k in _c:
        return _c[k]
    src = png(UI / pack / "Double", f"button_rectangle_{style}.png")
    s = 12
    out = Image.new("RGBA", (w, h))
    out.paste(src.crop((s, s, src.width - s, src.height - s)).resize((w - 2 * s, h - 2 * s)),
              (s, s))
    out.paste(src.crop((s, 0, src.width - s, s)).resize((w - 2 * s, s)), (s, 0))
    out.paste(src.crop((s, src.height - s, src.width - s, src.height)).resize((w - 2 * s, s)),
              (s, h - s))
    out.paste(src.crop((0, s, s, src.height - s)).resize((s, h - 2 * s)), (0, s))
    out.paste(src.crop((src.width - s, s, src.width, src.height - s)).resize((s, h - 2 * s)),
              (w - s, s))
    out.paste(src.crop((0, 0, s, s)), (0, 0))
    out.paste(src.crop((src.width - s, 0, src.width, s)), (w - s, 0))
    out.paste(src.crop((0, src.height - s, s, src.height)), (0, h - s))
    out.paste(src.crop((src.width - s, src.height - s, src.width, src.height)), (w - s, h - s))
    _c[k] = teinte(out, couleur) if couleur else out
    return _c[k]


class Monde:
    def __init__(self, haut=(12, 20, 46), bas=(30, 58, 138), horizon=650):
        self.im = Image.new("RGBA", (WW, WH), (0, 0, 0, 255))
        self.horizon = horizon
        self.sol_y = None       # la dernière surface marchée : c'est elle que
        self.props = []         # le moteur doit retrouver, pas une copie à mão
        self.tech = "left"
        self.degrade(haut, bas, horizon + 120)

    def degrade(self, haut, bas, stop):
        stop = min(WH, int(stop))
        t = np.linspace(0, 1, stop, dtype=np.float32)[:, None]
        a = np.array(haut, np.float32)[None, :]
        b = np.array(bas, np.float32)[None, :]
        ligne = a * (1 - t) + b * t                       # (stop, 3)
        pix = np.repeat(ligne[:, None, :], WW, 1).astype("uint8")
        self.im.paste(Image.fromarray(pix, "RGB").convert("RGBA"), (0, 0))

    def colle(self, im, x, y, alpha=255, miroir=False):
        """Colle en rognant hors du monde : une frise peut dépasser le cadre."""
        if miroir:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        x0, y0 = int(round(x)), int(round(y))
        cx0, cy0 = max(0, x0), max(0, y0)
        cx1, cy1 = min(WW, x0 + im.width), min(WH, y0 + im.height)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        v = im.crop((cx0 - x0, cy0 - y0, cx1 - x0, cy1 - y0))
        if alpha < 255:
            v = v.copy()
            v.putalpha(v.getchannel("A").point(lambda q: q * alpha // 255))
        self.im.alpha_composite(v, (cx0, cy0))

    def trace(self, traits, c=(30, 34, 42), epais=6, alpha=235):
        """Polylignes sur un seul calque : ce que Kenney ne livre pas en tuile.

        Le pack ne fournit qu'une chaîne verticale et une corde verticale : s'en
        servir de hauban ou de câble plaquait un bijou contre un mât au lieu
        d'une structure. Une diagonale ne peut être que tracée.
        """
        s = Image.new("RGBA", (WW, WH), (0, 0, 0, 0))
        d = ImageDraw.Draw(s)
        for pts in traits:
            d.line(pts, fill=(*c, alpha), width=epais, joint="curve")
        self.im.alpha_composite(s)

    def frise(self, d, nom, y, h=None, couleur=None, lum=1.0, alpha=255, x0=0, x1=WW):
        """Répète une frise tileable : les couches Kenney se recollent sans couture."""
        im = png(d, nom)
        if h and h != im.height:
            im = rhen(im, h)
        if couleur:
            im = teinte(im, couleur, lum)
        x = x0 - (x0 % im.width)
        while x < x1:
            self.colle(im, x, y, alpha)
            x += im.width

    def pave(self, d, nom, y0, y1, couleur=None, lum=1.0, alpha=255):
        """Pave en deux dimensions, à taille native — un mur de briques."""
        im = teinte(png(d, nom), couleur, lum) if couleur else png(d, nom)
        for y in range(int(y0), int(y1), im.height):
            for x in range(0, WW, im.width):
                self.colle(im, x, y, alpha)

    def pose(self, d, nom, x, pied, h, couleur=None, lum=1.0, alpha=255, miroir=False):
        """Sprite planté les pieds à la ligne `pied` — la profondeur s'y tient."""
        im = rhen(png(d, nom), h)
        if couleur:
            im = teinte(im, couleur, lum)
        if miroir:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        self.colle(im, x - im.width / 2, pied - im.height, alpha)
        return im

    def sol(self, y_top, famille="grass", couleur=(38, 66, 120), lum=1.0, liseré=None):
        """Sol de jeu vidéo : une rangée de blocs à face éclairée, puis le remplissage.

        « horizontal_middle » est proscrit comme surface : ses bords sont faits
        pour un débord de plateforme et le rang se lit alors comme une palissade.
        """
        tuile = teinte(png(PLT, f"terrain_{famille}_block_top.png"), couleur, lum)
        plein = teinte(png(PLT, f"terrain_{famille}_block_center.png"), couleur, lum * 0.8)
        self.sol_y = int(y_top)
        for y in range(int(y_top), WH, plein.height):
            im = tuile if y - y_top < tuile.height else plein
            for x in range(0, WW, im.width):
                self.colle(im, x, y)
        if liseré:
            r = Image.new("RGBA", (WW, 6, ), (*liseré, 220))
            self.colle(r, 0, y_top - 1)

    def ombre_portee(self, y, hauteur=150, noir=104):
        """Assombrit le bas du sol : sans cela les personnages flottent."""
        g = (np.linspace(0, 1, hauteur, dtype=np.float32) ** 1.5 * noir).astype(np.uint8)
        band = np.zeros((hauteur, WW, 4), np.uint8)
        band[..., 3] = np.repeat(g[:, None], WW, 1)
        self.im.alpha_composite(Image.fromarray(band, "RGBA"), (0, int(y)))

    def vignette(self, force=0.32):
        y, x = np.mgrid[0:WH, 0:WW].astype(np.float32)
        d = np.sqrt(((x - WW / 2) / (WW * .62)) ** 2 + ((y - WH / 2) / (WH * .66)) ** 2)
        m = np.clip((d - 0.55) / 0.75, 0, 1) ** 1.7 * force
        a = np.asarray(self.im, np.float32)
        a[..., :3] *= (1 - m[..., None])
        self.im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"), "RGBA")

    def prop(self, **kw):
        """Enregistre une pièce que le moteur devra animer, pas peindre.

        Le décor et sa liste de props sortent du même objet dans le même appel :
        ils ne peuvent pas se contredire, contrairement à une table tenue à la
        main des deux côtés. Le dessin statique reste dans la plaque, l'image
        vivante est décrite ici et rejouée frame par frame par render.py.
        """
        self.props.append(kw)

    def economise(self, nom):
        OUT.mkdir(exist_ok=True)
        f = OUT / f"plate_{nom}.webp"
        self.im.convert("RGB").save(f, quality=88)
        # Un run partiel ne doit pas effacer les treize autres décors.
        dest = OUT / "decors.json"
        tout = (json.loads(dest.read_text()) if dest.exists() else {})
        tout[nom] = dict(sol=self.sol_y, tech=self.tech, props=self.props)
        tout["_revision"] = datetime.now().isoformat(timespec="seconds")
        dest.write_text(json.dumps(tout, ensure_ascii=False, indent=1))
        return f


# --------------------------------------------------------------- pièces communes
def ciel_etoile(m, n=170, graine=4):
    k = ("etoiles", n, graine)
    if k not in _c:
        im = Image.new("RGBA", (WW, 520), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        r = np.random.default_rng(graine)
        for x, y, s, a in zip(r.random(n) * WW, r.random(n) * 500,
                              r.integers(2, 5, n), r.integers(70, 230, n)):
            d.ellipse([x, y, x + s, y + s], fill=(226, 238, 255, int(a)))
        _c[k] = im.filter(ImageFilter.GaussianBlur(0.4))
    m.colle(_c[k], 0, 0)


def lune(m, x=1660, y=150, diam=132):
    halo = Image.new("RGBA", (diam * 4, diam * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(halo)
    for i in range(diam * 2, 0, -6):
        d.ellipse([diam * 2 - i, diam * 2 - i, diam * 2 + i, diam * 2 + i],
                  fill=(150, 190, 255, int(7 * (1 - i / (diam * 2)))))
    m.colle(halo, x - diam * 2, y - diam * 2)
    m.colle(rhen(png(BEP, "moonFull.png"), diam), x - diam / 2, y - diam / 2)


def lueur(m, x, y, r, c, force=60):
    """Halo d'ampoule : des anneaux concentriques, pas de flou à chaque cadre."""
    im = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(r, 0, -4):
        d.ellipse([r - i, r - i, r + i, r + i],
                  fill=(*c, int(force * (1 - i / r) ** 1.6)))
    m.colle(im, x - r, y - r)


def lointain(m, y, c, lum=1.0, alpha=255):
    """Deux plans, pas un seul : montagnes derrière collines."""
    m.frise(BEE, "mountains.png", y, couleur=c, lum=lum, alpha=alpha)
    m.frise(BEE, "hillsLarge.png", y + 118, couleur=c, lum=lum * 0.82, alpha=alpha)


def village(m, pied, c, lum=1.0, pas=340, decal=90):
    """Quelques toits : un horizon habité, sans devenir une carte postale."""
    noms = ("house1.png", "tower.png", "house2.png", "castleWall.png")
    hauts = (150, 210, 132, 96)
    for i, x in enumerate(range(decal, WW + pas, pas)):
        m.pose(BEP, noms[i % 4], x, pied + (i % 3) * 6, hauts[i % 4], couleur=c, lum=lum)


def arbres(m, pied, c, lum=1.0, pas=196, decal=42, hbase=210):
    r = np.random.default_rng(11)
    noms = ["treePine.png", "tree.png", "treeLong.png", "treePine.png", "treeOrange.png"]
    for i, x in enumerate(range(decal, WW + pas, pas)):
        m.pose(BEP, noms[i % 5], x + int(r.integers(-24, 24)), pied,
               int(hbase + r.integers(-30, 46)), couleur=c, lum=lum, miroir=bool(i % 2))


def buissons(m, pied, c, lum=1.0, n=14):
    r = np.random.default_rng(5)
    for i in range(n):
        m.pose(BEP, ["bush1.png", "bush2.png", "bush3.png"][i % 3],
               float(r.integers(0, WW)), pied + int(r.integers(-6, 22)),
               int(r.integers(46, 86)), couleur=c, lum=lum)


def ecran(m, x, y, w, h, couleur=(20, 34, 74)):
    """Écran d'antenne : panneau bordé, fond de veille, barre de titre lumineuse."""
    m.colle(panneau(couleur, w, h, "depth_border"), x, y)
    m.colle(panneau((26, 44, 92), w - 44, h - 86, "flat"), x + 22, y + 62)
    m.colle(panneau(CYAN, w, 48, "depth_gloss"), x, y - 4)
    return x + 22, y + 62, w - 44, h - 86


def support(m, x, w, y_bas, pied, couleur=(26, 40, 74)):
    """Deux mâts sous un écran : sans eux, l'antenne flotte dans le ciel."""
    fût = panneau(couleur, 34, pied - y_bas, "flat")
    for fx in (x + w * 0.16, x + w * 0.84 - 34):
        m.colle(fût, fx, y_bas - 10)
        m.colle(panneau(couleur, 76, 26, "depth_flat"), fx - 21, pied - 26)


def emploi_du_temps(m, x, y, w, h, accent=CYAN):
    """Grille d'emploi du temps stylisée : des cases, des blocs, des coches.

    Rien de cela n'est une capture : aucune interface réelle ne passe à l'antenne.
    """
    cols, rows = 6, 5
    cw, ch = (w - 26) / cols, (h - 26) / rows
    r = np.random.default_rng(3)
    check = rhen(png(UI / "Blue" / "Double", "check_square_color_checkmark.png"),
                 int(min(40, ch - 12)))
    for j in range(int(rows)):
        for i in range(cols):
            bx, by = x + 13 + i * cw, y + 13 + j * ch
            m.colle(panneau((26, 44, 92), cw - 10, ch - 10, "line"), bx, by)
            if r.random() > 0.26:
                c = accent if r.random() > 0.3 else ORANGE
                m.colle(panneau(c, (cw - 10) * 0.62, ch - 22, "depth_flat"), bx + 5, by + 6)
            if r.random() > 0.70:
                m.colle(check, bx + cw - 52, by + 8)


def mot_cle(m, x, y, h):
    """Le nom du projet : notre propre image de marque, pas une génération."""
    im = rhen(png(ASSETS, "uniflow-wordmark-blanc-net-2400.png"), h)
    m.colle(im, x - im.width / 2, y - h / 2)


def ecusson(m, x, y, h):
    m.colle(rhen(png(ASSETS, "uniflow-ecusson-net-1024.png"), h), x - h / 2, y - h / 2)


def bulle(m, x, y, h, nom="emote_idea.png"):
    """Émoticônes Kenney : 16x16, agrandis au voisinage proche pour rester nets."""
    k = ("em", nom, h)
    if k not in _c:
        im = png(EM, nom)
        _c[k] = im.resize((max(1, round(im.width * h / im.height)), h), Image.NEAREST)
    m.colle(_c[k], x - _c[k].width / 2, y - h)


# --------------------------------------------------------------- mobilier de scène
def torche(m, x, y, lum=1.0):
    """Torche allumée : le support éteint porte la flampe, l'anneau de lumière dedans.

    Kenney livre la flamme en deux frames (torch_on_a / _b) : posée ici sur la
    première, elle sera échangée à l'image par le moteur — c'est ce qui fait
    vaciller un mur au lieu de le laisser peint.
    """
    m.colle(teinte(png(PLT, "torch_off.png"), (74, 58, 44), lum), x - 26, y - 26)
    f = rhen(teinte(png(PLT, "torch_on_a.png"), (255, 176, 64), lum), 86)
    m.colle(f, x - f.width / 2, y - f.height + 16)
    lueur(m, x, y - 26, 190, (255, 178, 74), force=54)


def fenetre(m, x, y, h, nuit=True):
    """Fenêtre Kenney (128×128) étirée en hauteur, avec sa traverse et sa lueur."""
    f = rhen(png(PLT, "window.png"), h)
    m.colle(teinte(f, (58, 44, 38)), x - f.width / 2, y)
    ciel = (18, 30, 66) if nuit else (168, 210, 240)
    m.colle(panneau(ciel, f.width - 34, h - 34, "flat"), x - f.width / 2 + 17, y + 17)
    lueur(m, x, y + h / 2, int(h * 0.85), ciel, force=26)
    return f.width


def tableau(m, x, y, w, h, craie=(222, 236, 246)):
    """Tableau noir : c'est un panneau de l'UI pack, pas une capture d'écran."""
    m.colle(panneau((62, 46, 34), w + 34, h + 34, "depth_border"), x - 17, y - 17)
    m.colle(panneau((22, 52, 44), w, h, "flat"), x, y)
    r = np.random.default_rng(7)
    for i in range(7):
        lw = int(w * (0.24 + 0.5 * r.random()))
        m.colle(panneau(craie, lw, 7, "flat"), x + 26, y + 30 + i * (h - 60) // 7)
    m.colle(panneau(ORANGE, int(w * 0.34), 9, "flat"), x + 26, y + 30 + 2 * (h - 60) // 7)
    m.colle(panneau((240, 240, 246), 92, 16, "depth_flat"), x + w - 110, y + h + 6)


def pupitre(m, x, pied, h=104, plateau_c=(150, 106, 62), assise=None):
    """Un pupitre : une planche sur deux tréteaux, et une chaise si on la veut."""
    plateau = rhen(teinte(png(PLT, "block_plank.png"), plateau_c), h)
    m.colle(plateau, x, pied - h)
    pied_gauche = rhen(teinte(png(PLT, "block_planks.png"), (96, 68, 44)), h)
    m.colle(pied_gauche, x + 10, pied - h + 6)
    m.colle(pied_gauche, x + plateau.width - h + 2, pied - h + 6)
    if assise:
        m.colle(rhen(teinte(png(PLT, "block_planks.png"), assise), int(h * .78)),
                x + plateau.width + 18, pied - int(h * .78))
    return plateau.width


def pilier(m, x, pied, h, couleur=(92, 96, 108), famille="stone"):
    """Pilier de moellons empilés, avec base et chapiteau plus larges que le fût."""
    bloc = teinte(png(PLT, f"terrain_{famille}_block_center.png"), couleur)
    b = rhen(png(PLT, f"terrain_{famille}_block_top.png"), bloc.height)
    for y in range(int(pied - h), int(pied), bloc.height):
        for dx in (0, bloc.width):
            m.colle(bloc, x - bloc.width + dx, y)
    m.colle(rhen(b, 54), x - bloc.width - 14, pied - h - 46)
    m.colle(rhen(b, 62), x - bloc.width - 18, pied - 56)


def drapeau(m, x, pied, h, couleur=(56, 214, 255), fanion="flag_blue_a.png",
            fanion_c=None):
    """Mât et fanion : le fanion de Kenney existe en deux frames, lui aussi.

    Le sprite porte déjà son propre mât en bois, centré à 15 % de sa largeur :
    posé à x+4 il doublait le nôtre d'un décalage visible dès que le fanion
    grandit. On l'aligne sur l'axe. « fanion_c » existe parce que le mât et la
    flamme ne peuvent pas porter la même teinte : sur le pylône de l'antenne, le
    rouge sur rouge ne laissait voir qu'un bâton.
    """
    m.colle(panneau(couleur, 14, h, "depth_flat"), x - 7, pied - h)
    f = rhen(teinte(png(PLT, fanion), fanion_c or couleur), int(h * .58))
    m.colle(f, x - .152 * f.width, pied - h + 6)
    m.colle(rhen(png(PLT, "coin_gold.png"), 34), x - 17, pied - h - 22)
    return f


def panneau_signal(m, x, pied, h, texte_c=(216, 190, 140)):
    """Panneau planté : le `sign.png` de Kenney sur son montant de bois."""
    m.colle(rhen(teinte(png(PLT, "block_planks.png"), (98, 70, 46)), h), x - 13, pied - h)
    s = rhen(teinte(png(PLT, "sign.png"), texte_c), int(h * .62))
    m.colle(s, x - s.width / 2, pied - h - s.height + 30)
    return s


def echelle(m, x, y_bas, n=4):
    m.colle(rhen(png(PLT, "ladder_bottom.png"), 128), x, y_bas - 128)
    for i in range(1, n):
        m.colle(rhen(png(PLT, "ladder_middle.png"), 128), x, y_bas - 128 * (i + 1))
    m.colle(rhen(png(PLT, "ladder_top.png"), 128), x, y_bas - 128 * (n + 1))


def lampadaire(m, x, pied, h=300, c=(252, 196, 96)):
    """Poteau + lanterne : l'éclairage public de toutes les scènes de nuit."""
    m.colle(panneau((34, 42, 62), 26, h, "depth_flat"), x - 13, pied - h)
    m.colle(panneau((34, 42, 62), 86, 24, "depth_flat"), x - 43, pied - 24)
    m.colle(panneau((34, 42, 62), 70, 20, "depth_gradient"), x - 35, pied - h - 26)
    lueur(m, x, pied - h + 6, 210, c, force=62)
    m.colle(panneau(c, 56, 40, "depth_gloss"), x - 28, pied - h - 6)


def banc(m, x, pied, w=250, c=(128, 92, 58)):
    m.colle(rhen(teinte(png(PLT, "block_planks.png"), c), 40), x, pied - 96)
    m.colle(rhen(teinte(png(PLT, "block_planks.png"), c), 30), x, pied - 186)
    for dx in (18, w - 58):
        m.colle(panneau((58, 48, 44), 40, 96, "flat"), x + dx, pied - 96)
    m.colle(panneau((58, 48, 44), w, 14, "flat"), x, pied - 96)


def foule(m, pied, n, h, pas, couleurs, lum=0.3, graine=3, formes=4, decal=90):
    """Rangs de silhouettes Kenney (shape-characters) : le public, sans visage détaillé.

    « decal » n'est pas un réglage de goût : la foule est posée sur la même
    ligne de sol que les deux hôtes, et sans elle le premier spectateur
    tiendrait exactement la place d'Archlord.
    """
    corps = ["circle", "squircle", "square", "rhombus"]
    visages = ["face_a.png", "face_i.png", "face_c.png", "face_f.png"]
    r = np.random.default_rng(graine)
    for i in range(n):
        x = int(r.integers(-40, WW)) if i >= len(couleurs) else decal + i * pas
        c = couleurs[i % len(couleurs)]
        b = rhen(teinte(png(SC, f"{c}_body_{corps[i % formes]}.png"), (205, 215, 235), lum), h)
        m.colle(b, x, pied - b.height + 12)
        v = rhen(png(SC, visages[i % 4]), int(h * 0.4))
        m.colle(v, x + b.width / 2 - v.width / 2, pied - b.height + 24)


def antenne(m, x, pied, h, c=(120, 128, 146)):
    """Mât treillis : deux montants, des échelons, et une travée en X par étage.

    Deux colonnes de planches empilées se lisaient comme une tour de caisses, et
    le second essai — `chain.png` posé en hauban — n'a fait que plaquer une
    chaîne verticale contre le pylône : le pack ne livre aucune diagonale. Ce
    sont elles qui font lire une structure, donc elles sont tracées.
    """
    n = max(2, int(h / 128))
    montant = panneau((98, 106, 124), 20, 128, "depth_flat")
    echelon = panneau((74, 82, 100), 124, 12, "flat")
    pourtour = [(x - 62, pied), (x - 62, pied - 128 * n),
                (x + 62, pied - 128 * n), (x + 62, pied)]
    m.trace([pourtour], (150, 158, 176), 9, 200)
    for i in range(n):
        y = pied - (i + 1) * 128
        m.trace([[(x - 62, y + 128), (x + 62, y)],
                 [(x + 62, y + 128), (x - 62, y)]], (86, 94, 112), 7)
        m.colle(echelon, x - 62, y + 58)
        for dx in (-72, 52):
            m.colle(montant, x + dx, y)
    m.colle(panneau(c, 210, 16, "flat"), x - 105, pied - 128 * n - 10)
    drapeau(m, x, pied - 128 * n - 6, 170, (74, 84, 104), "flag_red_a.png",
            fanion_c=(232, 76, 62))
    return pied - 128 * n - 176


def cable(m, x1, y1, x2, y2, pend=56, c=(30, 34, 42), gros=8, rompu=1.0):
    """Câble abattu : une chaînette qui pend d'un point à l'autre, coupée en route.

    Rend le point de rupture : le brin libre s'y suspend, ce qui évite de
    recopier à la main une coordonnée que le calcul connaît déjà.
    """
    n = 40
    ti = [i / n for i in range(int(n * rompu) + 1)]
    pts = [(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t + pend * 4 * t * (1 - t))
           for t in ti]
    m.trace([pts], c, gros)
    return pts[-1]


def brin(m, x, y, h, c=(30, 34, 42)):
    """Le tronçon libre qui pend après la rupture, terminé par sa chausse.

    La tuile `rope.png` fait 32 de large sur 128 : étirée à 230 de haut elle en
    faisait 57, soit une barre noire flottante. Une corde qui pend garde
    l'épaisseur du câble dont elle tombe — et c'est la chaîne de Kenney qui en
    fait l'embout, parce qu'elle seule dans le pack ressemble à du métal.
    """
    m.trace([[(x, y), (x + 6, y + h)]], c, 7)
    chausse = rhen(teinte(png(PLT, "chain.png"), (120, 128, 146)), 40)
    m.colle(chausse, x + 6 - chausse.width / 2, y + h - 12)


def pluie(m, n=260, graine=13, angle=-16, c=(176, 204, 236), a=64):
    """Averses en traits : un calque dessiné, pas un filtre — il ne bouge pas au zoom."""
    k = ("pluie", n, graine, angle)
    if k not in _c:
        im = Image.new("RGBA", (WW, WH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        r = np.random.default_rng(graine)
        for x, y, l in zip(r.random(n) * (WW + 200) - 100, r.random(n) * (WH - 180),
                           r.integers(26, 62, n)):
            d.line([x, y, x + l * np.sin(np.radians(-angle)), y + l * np.cos(np.radians(-angle))],
                   fill=(*c, int(a)), width=2)
        _c[k] = im
    m.colle(_c[k], 0, 0)



# --------------------------------------------------------------- les décors
def plateau(nom, crepuscule=False):
    """Le plateau d'antenne : ciel de studio, campus au loin, estrade de tuiles."""
    if crepuscule:
        m = Monde((34, 20, 62), (198, 96, 46), 660)
        loin, coll, herbe, estrade = (96, 60, 100), (58, 36, 76), (52, 82, 66), (120, 58, 44)
    else:
        m = Monde((6, 12, 34), (26, 52, 116), 650)
        ciel_etoile(m)
        lune(m)
        loin, coll, herbe, estrade = (34, 58, 108), (24, 44, 88), (28, 62, 78), (38, 66, 120)

    m.frise(BEE, "cloudLayerB2.png", 110, couleur=(255, 255, 255), lum=0.5, alpha=42)
    lointain(m, 400, loin, lum=1.1)
    village(m, 646, coll, lum=0.95)
    m.frise(BEE, "hills.png", 604, couleur=coll, lum=0.78)
    m.frise(BEE, "groundLayer2.png", 760, couleur=herbe, lum=0.9)
    arbres(m, 800, herbe, lum=0.8, pas=252, hbase=200)
    m.frise(BEE, "groundLayer1.png", 806, couleur=herbe, lum=1.0)

    # estrade : la ligne de sol du moteur (930) est portée par les tuiles
    m.sol(866, "stone", couleur=tuple(int(v * 0.7) for v in estrade), liseré=(120, 140, 180))
    m.sol(930, "grass", couleur=estrade, liseré=(150, 200, 150))
    m.ombre_portee(930, 150, 112)

    if crepuscule:
        support(m, 744, 560, 590, 806, (86, 52, 46))
        x0, y0, w0, h0 = ecran(m, 744, 322, 560, 268)
        emploi_du_temps(m, x0, y0, w0, h0, accent=ORANGE)
        mot_cle(m, 1024, 172, 92)
    else:
        support(m, 232, 516, 544, 806)
        support(m, 1300, 516, 544, 806)
        x0, y0, w0, h0 = ecran(m, 232, 272, 516, 272)
        emploi_du_temps(m, x0, y0, w0, h0)
        x1, y1, w1, h1 = ecran(m, 1300, 272, 516, 272)
        for i in range(3):
            m.colle(panneau((44, 78, 140), w1 - 40, 36, "depth_gradient"), x1 + 20, y1 + 18 + i * 52)
            m.colle(panneau(ORANGE if i == 1 else CYAN, (w1 - 60) * (0.86 - i * 0.2), 22,
                            "depth_flat"), x1 + 40, y1 + 25 + i * 52)
        mot_cle(m, 1024, 170, 92)
    for x in (138, 1910):
        m.pose(BEP, "treePalm.png", x, 1046, 320, couleur=(18, 40, 56), lum=0.9)
    m.vignette(0.30)
    return m.economise(nom)


def campus():
    """Les pelouses de Ngoa-Ekellé, en plein jour."""
    m = Monde((96, 160, 222), (212, 236, 246), 676)
    m.colle(rhen(png(BEP, "sun.png"), 152), 250, 86)
    m.frise(BEE, "cloudLayer1.png", 88, couleur=(255, 255, 255), lum=1.0, alpha=140)
    lointain(m, 398, (126, 162, 196))
    village(m, 662, (92, 130, 172))
    m.frise(BEE, "hillsLarge.png", 602, couleur=(58, 138, 94))
    m.frise(BEE, "groundLayer2.png", 752, couleur=(48, 120, 76))
    arbres(m, 800, (36, 100, 64), pas=236, hbase=240)
    m.sol(936, "sand", couleur=(196, 164, 104), liseré=(240, 224, 180))
    m.sol(1000, "grass", couleur=(56, 128, 80))
    # Allée pavée au premier plan : un rang de blocs francs, posé à plat.
    # Les dalles debout que nous avions ici portaient le galbe éclairé du bloc
    # « top » et se lisaient comme une rangée de tombes.
    m.pave(PLT, "terrain_sand_block_center.png", 1064, WH, couleur=(212, 198, 162))
    m.colle(Image.new("RGBA", (WW, 5), (246, 236, 206, 190)), 0, 1060)
    buissons(m, 1016, (38, 104, 64))
    m.pose(BEP, "treePalm.png", 300, 1052, 344, couleur=(52, 118, 74))
    m.pose(BEP, "treePalm.png", 1780, 1064, 376, couleur=(46, 108, 68), miroir=True)
    m.ombre_portee(1000, 152, 96)
    mot_cle(m, 1024, 152, 84)
    m.vignette(0.24)
    return m.economise("campus")


def demo():
    """Le mur d'interface : une salle de contrôle, pas une capture d'écran."""
    m = Monde((8, 14, 32), (18, 30, 62), 560)
    m.pave(PLT, "bricks_grey.png", 0, WH, couleur=(24, 38, 70), lum=0.85, alpha=150)
    m.frise(BEE, "cloudLayerB1.png", 80, couleur=(56, 214, 255), lum=0.5, alpha=22)
    for i in range(9):
        x = 92 + i * 218
        m.colle(panneau((30, 54, 104), 176, 84, "depth_gradient"), x, 168)
        m.colle(panneau(ORANGE if i % 3 else CYAN, 152, 24, "depth_gloss"), x + 12, 198)
    x0, y0, w0, h0 = ecran(m, 148, 300, 800, 464)
    emploi_du_temps(m, x0, y0, w0, h0)
    x1, y1, w1, h1 = ecran(m, 1092, 300, 806, 464)
    teintes = (CYAN, ORANGE, (120, 220, 160), (200, 190, 90))
    for i, frac in enumerate((0.92, 0.74, 0.58, 0.31)):
        m.colle(panneau((26, 44, 92), w1 - 60, 44, "line"), x1 + 30, y1 + 26 + i * 78)
        m.colle(panneau(teintes[i], (w1 - 120) * frac, 26, "depth_flat"), x1 + 60, y1 + 35 + i * 78)
        m.colle(panneau((240, 244, 252), 26, 26, "depth_gloss"),
                x1 + 66 + (w1 - 120) * frac, y1 + 33 + i * 78)
    ecusson(m, 1024, 132, 152)
    m.sol(880, "stone", couleur=(22, 36, 70), liseré=(70, 96, 150))
    m.sol(968, "stone", couleur=(34, 56, 104), liseré=(88, 116, 172))
    m.ombre_portee(968, 148, 120)
    # lampadaires plantés au fond de la salle, pied sur la première estrade
    for x in (268, 1780):
        lueur(m, x, 756, 170, (252, 196, 96), force=68)
        m.colle(panneau((72, 58, 40), 26, 116, "depth_flat"), x - 13, 764)
        m.colle(panneau((72, 58, 40), 74, 22, "depth_flat"), x - 37, 858)
        m.colle(panneau((252, 196, 96), 120, 34, "depth_gloss"), x - 60, 730)
    m.vignette(0.34)
    return m.economise("demo")


def compare():
    """Avant / après : à gauche la photo floue sur WhatsApp, à droite la plateforme."""
    m = Monde((38, 40, 46), (76, 80, 90), 640)
    lointain(m, 402, (66, 70, 82), lum=1.0)
    m.frise(BEE, "hills.png", 604, couleur=(58, 62, 74))
    m.frise(BEE, "groundLayer1.png", 800, couleur=(72, 76, 86))
    m.sol(1010, "stone", couleur=(68, 72, 84), liseré=(122, 128, 142))

    droit = Monde((22, 52, 116), (70, 150, 190), 640)
    ciel_etoile(droit, n=90, graine=9)
    lointain(droit, 402, (40, 78, 132))
    droit.frise(BEE, "hills.png", 604, couleur=(36, 96, 106))
    droit.frise(BEE, "groundLayer1.png", 800, couleur=(40, 96, 78))
    droit.sol(1010, "grass", couleur=(40, 84, 130), liseré=(96, 178, 140))
    arbres(droit, 900, (34, 92, 92), pas=280, hbase=150)

    # la coupure est nette : deux moitiés qu'on ne mélange pas en dégradé
    m.im.paste(droit.im.crop((1024, 0, WW, WH)), (1024, 0))
    m.colle(panneau((10, 14, 34), 44, WH, "flat"), 1002, 0)
    m.colle(panneau(ORANGE, 28, WH, "depth_gloss"), 1010, 0)
    croix = rhen(png(UI / "Red" / "Double", "icon_outline_cross.png"), 76)
    coche = rhen(png(UI / "Green" / "Double", "icon_outline_checkmark.png"), 76)
    for i in range(4):
        m.colle(croix, 300, 300 + i * 136)
        m.colle(coche, 1690, 300 + i * 136)
    m.ombre_portee(1010, 140, 108)
    m.vignette(0.28)
    return m.economise("compare")


def audience():
    """Le public : des rangs de petites silhouettes, vus depuis la scène."""
    m = Monde((10, 18, 44), (28, 52, 104), 520)
    ciel_etoile(m, n=110, graine=8)
    m.frise(BEE, "hillsLarge.png", 286, couleur=(30, 54, 98), lum=0.95)
    m.frise(PLB, "background_fade_hills.png", 372, couleur=(26, 46, 88), lum=0.75, alpha=170)

    corps = ["blue", "yellow", "pink", "green", "purple", "red"]
    formes = ["circle", "squircle", "square", "rhombus"]
    visages = ["face_a.png", "face_i.png", "face_c.png", "face_f.png"]
    r = np.random.default_rng(21)
    for rang in range(5):
        pied = 648 + rang * 96
        h = 64 + rang * 16
        m.colle(panneau((22, 38, 76), WW + 40, 58 + rang * 7, "depth_gradient"), -20, pied)
        pas = 172 - rang * 9
        for i in range(-1, 14):
            x = 86 + i * pas + int(r.integers(-13, 13))
            j = (i + rang) % 6
            b = rhen(teinte(png(SC, f"{corps[j]}_body_{formes[(i + rang) % 4]}.png"),
                            (205, 215, 235), lum=0.28 + rang * 0.15), h)
            m.colle(b, x, pied - b.height + 12)
            if rang >= 2 and (i + rang) % 3:
                v = rhen(png(SC, visages[(i + rang) % 4]), int(h * 0.4))
                m.colle(v, x + b.width / 2 - v.width / 2, pied - b.height + 24)
    m.sol(1035, "grass", couleur=(30, 52, 96), liseré=(74, 116, 168))
    m.ombre_portee(1035, 116, 124)
    for i, n in enumerate(("emote_idea.png", "emote_question.png", "emote_alert.png")):
        bulle(m, 430 + i * 620, 566 - i * 44, 116, n)
    m.vignette(0.32)
    return m.economise("audience")


def backstage():
    """L'envers du décor : pierre, planches, câbles, une lampe qui pend."""
    m = Monde((16, 18, 26), (40, 36, 42), 600)
    m.pave(PLT, "bricks_grey.png", 0, 1000, couleur=(56, 50, 46), lum=0.95, alpha=200)
    m.frise(BEE, "cloudLayerB1.png", 120, couleur=(36, 32, 30), lum=0.9, alpha=60)
    chaine = rhen(png(PLT, "chain.png"), 68)
    for x in (624, 1372):
        for i in range(11):
            m.colle(chaine, x, 96 + i * 56)
        m.colle(panneau((252, 196, 96), 96, 30, "depth_gloss"), x - 48, 96 + 11 * 56)
        lueur(m, x, 96 + 11 * 56 + 15, 165, (252, 196, 96), force=55)
        m.colle(panneau((60, 48, 30), 34, 120, "depth_flat"), x - 17, 96 + 11 * 56 + 24)
    # piliers du plafond au plancher : un moellon qui s'arrête en l'air ne
    # raconte rien d'autre qu'une erreur de calque
    chapiteau = teinte(png(PLT, "terrain_stone_block_top.png"), (96, 84, 76))
    for x in (236, 948, 1668):
        m.colle(panneau((58, 50, 46), 112, 985, "border"), x, 0)
        m.colle(rhen(chapiteau, 56), x - 8, 985 - 56)
        m.colle(rhen(chapiteau, 44), x - 6, 0)
        m.colle(panneau((252, 196, 96), 78, 22, "depth_gloss"), x + 17, 132)
    caisse = teinte(png(PLT, "block_plank.png"), (152, 110, 64))
    r = np.random.default_rng(31)
    for i in range(9):
        x = 116 + i * 224 + int(r.integers(-24, 24))
        h = int(r.integers(140, 210))
        m.colle(rhen(caisse, h), x, 985 - h)
        if i % 3 == 0:
            m.colle(rhen(caisse, int(h * 0.66)), x + 22, int(985 - h * 1.62))
    m.sol(985, "dirt", couleur=(74, 60, 48), liseré=(126, 104, 82))
    m.ombre_portee(985, 150, 128)
    m.vignette(0.40)
    return m.economise("backstage")


# --------------------------------------------------------------- six scènes de plus
def amphi():
    """L'amphithéâtre : mur de briques, tableau, rangs de pupitres sous les fenêtres."""
    m = Monde((18, 22, 40), (46, 40, 52), 520)
    m.pave(PLT, "bricks_brown.png", 0, 1010, couleur=(86, 60, 50), lum=0.95, alpha=235)
    m.frise(BEE, "cloudLayerB1.png", 90, couleur=(60, 44, 40), lum=0.9, alpha=48)
    # le fond de la salle : trois hautes fenêtres ouvertes sur la nuit
    for x in (268, 1024, 1780):
        fenetre(m, x, 150, 430, nuit=True)
        torche(m, x - 250, 470)
        torche(m, x + 250, 470)
    tableau(m, 664, 250, 720, 330)
    m.colle(panneau((240, 240, 246), 300, 18, "depth_flat"), 874, 604)
    # trois rangs de pupitres, de plus en plus bas et de plus en plus près
    for rang, (pied, h, pas, decal) in enumerate(((742, 86, 268, 96),
                                                  (846, 100, 292, 40),
                                                  (958, 118, 320, -16))):
        m.colle(panneau((58, 44, 38), WW + 60, 22, "flat"), -30, pied - 6)
        for i in range(7 - rang):
            x = decal + 250 + i * pas
            pupitre(m, x, pied, h, (152, 108, 64), assise=(104, 74, 48))
    m.colle(rhen(teinte(png(PLT, "door_closed.png"), (104, 74, 52)), 330), 1868, 680)
    m.colle(rhen(teinte(png(PLT, "lock_red.png"), (232, 96, 84)), 74), 2004, 838)
    m.sol(1010, "dirt", couleur=(74, 54, 42), liseré=(150, 116, 84))
    m.pave(PLT, "block_planks.png", 1010, WH, couleur=(120, 86, 56), lum=0.9)
    m.ombre_portee(1010, 148, 120)
    mot_cle(m, 1024, 116, 78)
    m.vignette(0.38)
    return m.economise("amphi")


def portail():
    """Le portail de l'université, en plein jour : deux piliers, la grille, le panneau."""
    m = Monde((92, 156, 224), (206, 234, 246), 660)
    m.colle(rhen(png(BEP, "sun.png"), 148), 1724, 96)
    m.frise(BEE, "cloudLayer2.png", 96, couleur=(255, 255, 255), lum=1.0, alpha=150)
    lointain(m, 384, (122, 158, 194))
    village(m, 648, (96, 132, 172), pas=372)
    m.frise(BEE, "hillsLarge.png", 596, couleur=(58, 136, 92))
    m.frise(BEE, "groundLayer2.png", 748, couleur=(50, 122, 78))
    arbres(m, 806, (36, 100, 64), pas=268, hbase=224)
    # la grille : du liseré de ferraille entre les deux piliers, jamais sur les piliers
    for x in range(556, 1512, 128):
        m.colle(rhen(teinte(png(PLT, "fence.png"), (78, 86, 100)), 236), x, 774)
    for x in (430, 1618):
        pilier(m, x, 1006, 620, (150, 146, 138))
        drapeau(m, x, 386, 190, (56, 168, 116), "flag_green_a.png")
    m.colle(panneau((126, 118, 104), 1188, 74, "depth_gradient"), 430, 372)
    panneau_signal(m, 1024, 470, 190, (232, 214, 168))
    m.sol(1006, "sand", couleur=(200, 172, 116), liseré=(244, 228, 186))
    m.pave(PLT, "terrain_sand_block_center.png", 1072, WH, couleur=(214, 200, 164))
    m.colle(Image.new("RGBA", (WW, 5), (248, 238, 210, 190)), 0, 1068)
    buissons(m, 1012, (40, 106, 66), n=12)
    m.pose(BEP, "treePalm.png", 186, 1060, 356, couleur=(52, 118, 74))
    m.pose(BEP, "treePalm.png", 1880, 1068, 388, couleur=(46, 108, 68), miroir=True)
    foule(m, 1006, 7, 116, 236, ("yellow", "green", "red", "blue"), lum=0.42,
          graine=17, decal=102)
    m.ombre_portee(1006, 150, 92)
    mot_cle(m, 1024, 148, 82)
    m.vignette(0.22)
    return m.economise("portail")


def reseau():
    """L'orage : l'antenne muette, les flaques, et l'écran qui a tout gardé quand même."""
    m = Monde((40, 50, 72), (92, 106, 130), 640)
    m.frise(BEE, "cloudLayerB1.png", 40, couleur=(52, 60, 78), lum=1.0, alpha=200)
    m.frise(BEE, "cloudLayerB2.png", 150, couleur=(42, 50, 68), lum=1.0, alpha=180)
    m.frise(BEE, "mountainA.png", 400, couleur=(56, 66, 86), lum=1.0, alpha=200)
    m.frise(BEE, "hills.png", 560, couleur=(46, 58, 76))
    m.frise(BEE, "groundLayer1.png", 762, couleur=(40, 50, 68))
    for x in (332, 1716):
        m.pose(BEP, "treeDead.png", x, 866, 330, couleur=(34, 40, 52), lum=1.0)
    antenne(m, 700, 940, 700)
    # le pylône de secours, à gauche : c'est à lui que le câble tenait
    m.colle(panneau((62, 70, 88), 26, 300, "depth_flat"), 138, 640)
    m.colle(panneau((62, 70, 88), 120, 18, "flat"), 92, 660)
    # les câbles abattus : une chaînette du mât à la souche, sectionnée en route
    xb, yb = cable(m, 690, 452, 152, 636, pend=70, rompu=.68)
    brin(m, xb, yb, 230)
    xc, yc = cable(m, 712, 540, 1040, 902, pend=52, rompu=.44)
    brin(m, xc, yc, 168)
    x0, y0, w0, h0 = ecran(m, 1332, 470, 470, 300)
    m.colle(panneau((34, 46, 72), w0, h0, "flat"), x0, y0)
    bulle(m, x0 + w0 / 2 - 74, y0 + h0 / 2 + 46, 132, "emote_cloud.png")
    m.colle(rhen(png(UI / "Red" / "Double", "icon_outline_cross.png"), 96),
            x0 + w0 / 2 + 22, y0 + h0 / 2 - 60)
    for i in range(3):
        m.colle(panneau(CYAN, (w0 - 60) * (0.8 - i * 0.22), 20, "depth_flat"),
                x0 + 30, y0 + h0 - 82 + i * 26)
    support(m, 1332, 470, 770, 940, (40, 46, 58))
    m.sol(940, "stone", couleur=(62, 72, 92), liseré=(124, 138, 162))
    # la poutre arrachée gît au premier plan : après le sol, sinon le sol la boit
    m.trace([[(120, 1046), (392, 992)]], (96, 106, 128), 24, 255)
    m.trace([[(150, 1040), (370, 998)]], (140, 152, 176), 6, 210)
    # flaques : la surface d'eau étirée à plat. Une flaque est large et basse ;
    # `rhen` la gardait carrée et on lisait quatre carreaux de céramique.
    eau = teinte(png(PLT, "water_top.png").crop((0, 0, 128, 44)), (122, 158, 196))
    for x, w in ((300, 300), (840, 220), (1420, 380), (1880, 260)):
        m.colle(eau.resize((w, 40)), x, 972 + (w % 60))
    pluie(m, n=320, graine=23, angle=-14, a=54)
    m.ombre_portee(940, 150, 104)
    m.vignette(0.28)
    return m.economise("reseau")


def sentinelle():
    """Le rempart : verrou, bannières, torches — la sécurité sans un mot technique."""
    m = Monde((10, 16, 38), (30, 40, 78), 540)
    ciel_etoile(m, n=130, graine=6)
    lune(m, x=352, y=176, diam=118)
    m.pave(PLT, "bricks_grey.png", 240, 1000, couleur=(52, 60, 84), lum=0.95)
    # créneaux : un bloc franc tous les deux, jamais un rang continu
    creneau = teinte(png(PLT, "terrain_stone_block_top.png"), (66, 76, 104))
    for i, x in enumerate(range(0, WW, 128)):
        if i % 2 == 0:
            m.colle(rhen(creneau, 96), x, 150)
    m.colle(panneau((38, 46, 70), WW, 40, "depth_gradient"), 0, 232)
    for x in (232, 1816):
        pilier(m, x, 1000, 700, (72, 82, 112))
        torche(m, x, 560)
    for x in (624, 1424):
        torche(m, x, 520)
        banniere = panneau(CYAN, 150, 330, "depth_gradient")
        m.colle(banniere, x - 75, 300)
        m.colle(rhen(png(ASSETS, "uniflow-ecusson-net-1024.png"), 116), x - 58, 360)
    # le portail verrouillé, au centre
    m.colle(rhen(teinte(png(PLT, "door_closed.png"), (84, 66, 52)), 470), 808, 530)
    m.colle(panneau((62, 70, 96), 540, 46, "depth_border"), 774, 496)
    m.colle(rhen(png(PLT, "lock_red.png"), 150), 964, 700)
    m.colle(rhen(png(PLT, "key_gold.png" if (PLT / "key_gold.png").exists()
                    else "key_yellow.png"), 96), 1180, 856)
    # les rocs bordent l'estrade, ils ne la tiennent pas : à 392 et 1656 ils
    # repoussaient chacun des deux hôtes hors de leur quart de cadre
    for x in (180, 1860):
        m.colle(rhen(teinte(png(PLT, "rock.png"), (58, 64, 84)), 150), x, 930)
    m.sol(1000, "stone", couleur=(46, 54, 80), liseré=(94, 110, 150))
    m.ombre_portee(1000, 148, 126)
    m.vignette(0.40)
    return m.economise("sentinelle")


def avenir():
    """L'aube et l'échafaudage : ce qui se construit encore, littèrement."""
    m = Monde((40, 26, 68), (246, 168, 96), 700)
    halo = Image.new("RGBA", (760, 760), (0, 0, 0, 0))
    d = ImageDraw.Draw(halo)
    for i in range(380, 0, -8):
        d.ellipse([380 - i, 380 - i, 380 + i, 380 + i],
                  fill=(255, 208, 128, int(11 * (1 - i / 380))))
    m.colle(halo, 1180, 300)
    m.colle(rhen(png(BEP, "sun.png"), 210), 1455, 585)
    m.frise(BEE, "cloudLayer1.png", 120, couleur=(255, 214, 170), lum=1.0, alpha=110)
    m.frise(BEE, "mountainB.png", 430, couleur=(104, 66, 92), lum=1.0, alpha=210)
    m.frise(BEE, "hillsLarge.png", 556, couleur=(76, 52, 74))
    # des gradins d'herbe qui montent vers la droite : le chemin qui reste
    paliers = ((0, 900), (412, 830), (824, 762), (1236, 694), (1648, 626))
    for x0, y in paliers:
        tuile = teinte(png(PLT, "terrain_grass_block_top.png"), (58, 112, 74))
        plein = teinte(png(PLT, "terrain_grass_block_center.png"), (44, 84, 60), 0.8)
        for i, x in enumerate(range(x0, min(WW, x0 + 412), 128)):
            for k, yy in enumerate(range(y, WH, 128)):
                m.colle(tuile if k == 0 else plein, x, yy)
    echelle(m, 356, 900, 3)
    echelle(m, 1180, 762, 2)
    # l'échafaudage du haut : planches sur montants, et sa bâche
    for x in (1700, 1936):
        m.colle(rhen(teinte(png(PLT, "block_planks.png"), (126, 92, 58)), 300), x, 326)
    m.colle(rhen(teinte(png(PLT, "block_plank.png"), (150, 112, 70)), 300), 1660, 326)
    m.colle(panneau((206, 190, 166), 250, 190, "border"), 1706, 118)
    drapeau(m, 1476, 626, 210, (56, 214, 255))
    drapeau(m, 1888, 300, 180, ORANGE, "flag_yellow_a.png")
    for x in (150, 640, 1010):
        m.pose(BEP, "treePineOrange.png", x, 900 if x < 412 else 830, 250,
               couleur=(58, 74, 60), lum=0.9)
    m.ombre_portee(900, 150, 96)
    mot_cle(m, 1024, 132, 88)
    m.vignette(0.26)
    return m.economise("avenir")


def forum():
    """La place du soir : lampadaires, bancs, tableau d'affichage et questions en l'air."""
    m = Monde((16, 24, 56), (58, 74, 122), 620)
    ciel_etoile(m, n=140, graine=14)
    lune(m, x=1690, y=160, diam=120)
    m.frise(BEE, "cloudLayerB2.png", 130, couleur=(255, 255, 255), lum=0.5, alpha=34)
    lointain(m, 356, (44, 66, 112), lum=1.05)
    village(m, 640, (36, 56, 98), pas=318, decal=60)
    m.frise(BEE, "hills.png", 596, couleur=(30, 52, 86))
    m.frise(BEE, "groundLayer1.png", 760, couleur=(34, 58, 92))
    # le bâtiment de la place, ses fenêtres allumées et sa porte
    m.colle(panneau((44, 56, 92), 720, 470, "border"), 664, 470)
    m.colle(panneau((30, 40, 72), 660, 400, "flat"), 694, 500)
    for i in range(3):
        for j in range(2):
            fenetre(m, 790 + i * 220, 540 + j * 168, 128, nuit=False)
    m.colle(rhen(teinte(png(PLT, "door_open.png"), (252, 208, 138)), 260), 964, 680)
    m.colle(panneau((62, 76, 118), 780, 56, "depth_gradient"), 634, 442)
    for x in (138, 1910):
        m.pose(BEP, "treePalm.png", x, 1010, 340, couleur=(20, 42, 62), lum=0.9)
    for x in (300, 1024, 1748):
        lampadaire(m, x, 1000, 330)
    for x in (520, 1330):
        banc(m, x, 1000)
    panneau_signal(m, 1560, 872, 240, (226, 206, 158))
    for i, (dx, dy) in enumerate(((-70, -150), (10, -190), (86, -140), (-30, -96))):
        m.colle(panneau((244, 244, 250) if i % 2 else CYAN, 96, 74, "depth_flat"),
                1560 + dx, 872 - 240 + dy)
    m.sol(1000, "stone", couleur=(46, 58, 92), liseré=(104, 128, 172))
    m.pave(PLT, "terrain_stone_block_center.png", 1064, WH, couleur=(56, 68, 104), lum=0.9)
    # la foule reste en retrait d'un demi-passage : sur la même ligne que les
    # deux hôtes, un spectateur de 128 px pousserait dans leurs jambes
    foule(m, 946, 6, 128, 300, ("purple", "blue", "yellow"), lum=0.34, graine=29)
    for i, n in enumerate(("emote_idea.png", "emote_question.png", "emote_hearts.png")):
        bulle(m, 470 + i * 560, 700 - i * 66, 124, n)
    m.ombre_portee(1000, 148, 118)
    mot_cle(m, 1024, 132, 84)
    m.vignette(0.32)
    return m.economise("forum")


DECORS = {
    "wide": lambda: plateau("wide"),
    "medium": lambda: plateau("medium"),
    "outro": lambda: plateau("outro", crepuscule=True),
    "demo": demo,
    "campus": campus,
    "compare": compare,
    "audience": audience,
    "backstage": backstage,
    "amphi": amphi,
    "portail": portail,
    "reseau": reseau,
    "sentinelle": sentinelle,
    "avenir": avenir,
    "forum": forum,
}


if __name__ == "__main__":
    for cle in (sys.argv[1:] or DECORS):
        f = DECORS[cle]()
        print(f"{cle:10s} -> {f.name}   {f.stat().st_size / 1024:.0f} Ko")
