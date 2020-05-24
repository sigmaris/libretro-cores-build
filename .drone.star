def main(ctx):
    return [
        pipeline("bullseye", "computers", "81,atari800,blueMSX,CrocoDS,dosbox,fmsx,fs-uae,fuse,hatari,NP2,NP2kai,pcem,px68k,stella"),
        pipeline("bullseye", "consoles", "4do,handy,o2em,prosystem,vecx,virtualjaguar"),
        pipeline("bullseye", "misc", "2048,3dengine,Craft,Dinothawr,freej2me,gme,lutro,mrboom,nxengine,PocketCDG,prboom,scummvm,tyrquake,xrick"),
        pipeline("bullseye", "beetle", "beetle*"),
#        pipeline("bullseye", "mame", "mame"),
        pipeline("bullseye", "fba", "fbalpha*"),
        pipeline("bullseye", "nintendo", "bsnes,citra,desmume,dolphin,fceumm,gambatte,gpsp,gw,melonDS,meteor,mgba*,mupen64plus,nestopia,parallel-n64,PokeMini,QuickNES_Core,SameBoy,snes9x,snes9x2005,snes9x2010,tgbdual,vba-next,vbam"),
        pipeline("bullseye", "sega", "Genesis-Plus-GX,flycast,PicoDrive,redream,reicast"),
        pipeline("bullseye", "sony", "pcsx*,ppsspp"),
    ]


def pipeline(suite, name, pattern):
    return {
        "kind": "pipeline",
        "type": "docker",
        "name": "build_%s" % name,
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
                "image": "sigmaris/libretrobuilder:%s" % suite,
                "commands": [
                    "mkdir /drone/build",
                    "cd /drone/build",
                    "python3 /drone/src/core_builder.py --include '%s' %s" % (pattern, suite),
                ],
            },
        ],
    }
