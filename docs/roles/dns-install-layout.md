# DNS Install Layout

This note summarizes how the `dns` role currently models BIND/named on each
supported platform, and where that differs from the layout installed by the
distribution package manager.

The important distinction is:

- `Repo expects`: what `ansible-enterprise` currently generates.
- `Package default on disk`: what the distro package layout appears to use by
  default.

The package-default column is a working reference for future generator fixes.

| Distro / family | Repo expects | Package default on disk | Likely status |
|---|---|---|---|
| Debian | `/etc/bind/named.conf.local` + `/etc/bind/named.conf.options`; dynamic zones in `/var/lib/bind`; no chroot logic in repo | Debian docs match the config layout; dynamic zone/journal data belongs under `/var/lib/bind`, while slave/stub/cache data belongs under `/var/cache/bind`; chroot is optional, not default | Mostly aligned |
| Ubuntu | same as Debian | Inferred to follow Debian `bind9` layout | Probably aligned |
| Devuan | same as Debian | Inferred to follow Debian `bind9` layout | Probably aligned |
| openSUSE 15.6 / 16.0 | `/etc/named.conf`, zones in `/var/named`, `root:named`, `0770`, no chroot logic | `/etc/named.conf`; tmpfiles creates `/var/lib/named` as `root:named` `1775`; there is a separate `bind-chrootenv` package for chroot support | Mismatch |
| RHEL / Alma / Rocky / Fedora | `/etc/named.conf`, zones in `/var/named`, no chroot logic | Red Hat docs use `/etc/named.conf` and `/var/named`; `bind-chroot` / `named-chroot` is optional, not default | Mostly aligned |
| Arch | `/etc/named.conf`, zones in `/var/named`, no chroot logic | Arch package file list shows `/etc/named.conf` and `/var/named`; exact packaged permissions not verified here | Likely aligned |
| Alpine | repo writes `/etc/bind/named.conf`; zones in `/var/bind`; no chroot logic | Alpine package contents ship `/etc/bind/named.conf.authoritative` and `/etc/bind/named.conf.recursive`, with zone/root data under `/var/bind`; OpenRC service is `named` | Partial mismatch |
| Gentoo | `/etc/named.conf`, zones in `/var/named`, no chroot logic | Gentoo docs use `/etc/bind/named.conf` with `directory "/var/bind"`; chroot is optional via `CHROOT` in `/etc/conf.d/named` | Mismatch |
| FreeBSD with `bind918` package | `/usr/local/etc/namedb/named.conf`; zones in `/usr/local/etc/namedb`; no chroot logic | `bind918` package installs under `/usr/local/etc/namedb`; chroot support exists, but it is not treated as the default here | Likely aligned |

## Current Role Layout Matrix

This is the current generated path matrix for the role itself.

| Distro / family | Package | Service | Main config written by role | Zone dir | Zone dir owner:group | Zone dir mode | Chroot in repo? |
|---|---|---|---|---|---|---|---|
| Debian / Ubuntu / Devuan | `bind9` | `bind9` | `/etc/bind/named.conf.local` plus `/etc/bind/named.conf.options` | `/var/lib/bind` | `root:bind` | managed only on non-Debian, so no explicit mode set here | No |
| Alpine | `bind` | `named` | `/etc/bind/named.conf` | `/var/bind` | `root:named` | `0770` | No |
| Alma / Rocky / Fedora / RedHat | `bind` | `named` | `/etc/named.conf` | `/var/named` | `root:named` | `0770` | No |
| openSUSE 15.6 / 16.0 | `bind` | `named` | `/etc/named.conf` | currently generated as `/var/named` | `root:named` | `0770` | No |
| Arch | `bind` | `named` | `/etc/named.conf` | `/var/named` | `root:named` | `0770` | No |
| Gentoo | `bind` | `named` | `/etc/named.conf` | `/var/named` | `root:named` | `0770` | No |
| FreeBSD | `bind918` | `named` | `/usr/local/etc/namedb/named.conf` | `/usr/local/etc/namedb` | `root:bind` | `0770` | No |

## Confirmed Mismatches

- openSUSE package defaults use `/var/lib/named` with `root:named` and mode
  `1775`, while the generator currently treats openSUSE like generic
  non-Debian Linux and uses `/var/named` with `0770`.
- Gentoo package/docs use `/etc/bind/named.conf` and `/var/bind`, while the
  generator currently uses `/etc/named.conf` and `/var/named`.
- Alpine packages ship authoritative/recursive template variants, while the
  generator assumes a single `/etc/bind/named.conf`.

## Notes

- The repository does not currently implement explicit BIND chroot handling on
  any platform.
- Debian-family layout is the closest match today.
- The openSUSE and Gentoo path assumptions should be revisited in the
  generator.
