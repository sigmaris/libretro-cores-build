def main(ctx):
    return [
        pipeline(ctx, "bullseye", "computers", "81,atari800,blueMSX,CrocoDS,dosbox,fmsx,fs-uae,fuse,hatari,NP2,NP2kai,pcem,px68k,stella"),
        pipeline(ctx, "bullseye", "consoles", "4do,handy,o2em,prosystem,vecx,virtualjaguar"),
        pipeline(ctx, "bullseye", "misc", "2048,3dengine,Craft,Dinothawr,freej2me,gme,lutro,mrboom,nxengine,PocketCDG,prboom,scummvm,tyrquake,xrick"),
        pipeline(ctx, "bullseye", "beetle1", "beetle-bsnes,beetle-gba,beetle-lynx,beetle-ngp,beetle-pce-fast,beetle-pcfx"),
        pipeline(ctx, "bullseye", "beetle2", "beetle-psx,beetle-saturn,beetle-supergrafx,beetle-vb,beetle-wswan"),
#        pipeline(ctx, "bullseye", "mame", "mame"),
        pipeline(ctx, "bullseye", "fba", "fbalpha*,fbneo"),
        pipeline(ctx, "bullseye", "nintendo1", "bsnes*,citra,desmume,dolphin,fceumm,gambatte,gpsp,gw,melonDS,meteor,mgba*,mupen64plus"),
        pipeline(ctx, "bullseye", "nintendo2", "nestopia,parallel-n64,PokeMini,QuickNES_Core,SameBoy,snes9x,snes9x2005,snes9x2010,tgbdual,vba-next,vbam"),
        pipeline(ctx, "bullseye", "sega", "Genesis-Plus-GX,flycast,PicoDrive,redream,reicast,yabause"),
        pipeline(ctx, "bullseye", "sony", "pcsx*,ppsspp"),
    ]


def pipeline(ctx, suite, name, pattern):
    if ctx.build.event == "tag" and "-pre" in ctx.build.ref:
        prerelease = True
    else:
        prerelease = False

    return {
        "kind": "pipeline",
        "type": "docker",
        "name": name,
        "platform": {
            "os": "linux",
            "arch": "arm64",
        },
        "workspace": {
            "base": "/drone",
            "path": "src",
        },
        "trigger": {
            "ref": [
                "refs/heads/master",
                "refs/tags/*",
            ]
        },
        "steps": [
            {
                "name": "build",
                "image": "ghcr.io/sigmaris/libretrobuilder:%s" % suite,
                "commands": [
                    "mkdir /drone/build",
                    "cd /drone/build",
                    "python3 /drone/src/core_builder.py --build-number $DRONE_BUILD_NUMBER --include '%s' %s" % (pattern, suite),
                ],
            },
            {
                "name": "publish",
                "image": "ghcr.io/sigmaris/drone-github-release:latest",
                "settings": {
                    "api_key": {
                        "from_secret": "github_token",
                    },
                    "prerelease": prerelease,
                    "files": [
                        "/drone/build/*.deb",
                        "/drone/build/*.buildinfo",
                        "/drone/build/*.changes",
                    ],
                },
                "depends_on": ["build"],
                "when": {
                    "event": "tag",
                },
            },
        ],
    }
