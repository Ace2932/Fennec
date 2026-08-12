"""Every topic the Teensy publishes appears in the firmware contract README.

WHY THIS EXISTS. On 2026-08-10 two firmware publishers turned out to be
undocumented, and the omission had already produced a downstream bug:

    main.cpp publishes  /servo_voltage      (12 floats, 5 Hz)
    main.cpp publishes  /servo_temperature  (12 floats, 5 Hz)

Neither was in `firmware/teensy/firmware/README.md`, which
`nova_ops/dashcam/topics.py` names IN ITS OWN DOCSTRING as the source of the
names it uses:

    "Names match the firmware contract in firmware/teensy/firmware/README.md."

With nothing to copy from, the dashcam guessed: it listed `/joint_voltages`
and `/joint_temperatures` in PENDING_TOPICS, annotated "firmware stub". Those
names match nothing the firmware ever published, so the dashcam recorded
neither -- while its comment said it was still waiting for firmware that had
in fact landed. A stale blocker and a name mismatch, compounding, on the exact
signals you would want after a servo browns out or cooks.

THE SHAPE, which is why this is a gate and not a one-line fix: nothing could
have caught it. Both sides were internally consistent. The firmware published
correctly; the dashcam subscribed correctly; no test asserted the two halves
referred to the same string, because no test spanned them. This is the
[[interface-boundary-bugs]] class -- each component right, the SEAM wrong --
and a seam is only checkable from outside both components.

WHAT THIS DOES NOT CHECK. That the topic is USEFUL, that anyone subscribes, or
that the rate/type in the README is accurate. It checks one thing: a published
topic is written down where the rest of the system is told to look. That is
the property whose absence produced the bug.
"""

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[4]
MAIN_CPP = REPO / "firmware/teensy/firmware/src/main.cpp"
FW_README = REPO / "firmware/teensy/firmware/README.md"

#: Publishers that are deliberately absent from the contract table, with the
#: reason. Keep this EMPTY unless there is a real one -- an allow-list is how a
#: gate quietly stops gating. Each entry must say why, not just what.
UNDOCUMENTED_OK: dict[str, str] = {}

_SUB_RE = re.compile(
    r"rclc_subscription_init_(?:default|best_effort)\s*\(\s*"
    r"&\w+\s*,\s*&\w+\s*,\s*"
    r"ROSIDL_GET_MSG_TYPE_SUPPORT\([^)]*\)\s*,\s*"
    r'"([A-Za-z0-9_/]+)"',
    re.S,
)

_PUB_RE = re.compile(
    r"rclc_publisher_init_(?:default|best_effort)\s*\(\s*"
    r"&\w+\s*,\s*&\w+\s*,\s*"
    r"ROSIDL_GET_MSG_TYPE_SUPPORT\([^)]*\)\s*,\s*"
    r'"([A-Za-z0-9_/]+)"',
    re.S,
)


def _published_topics() -> set[str]:
    return set(_PUB_RE.findall(MAIN_CPP.read_text()))


def _subscribed_topics() -> set[str]:
    return set(_SUB_RE.findall(MAIN_CPP.read_text()))


def _documented_topics() -> set[str]:
    """Topic names in a `| Pub |` or `| Sub |` row of the README."""
    return _documented(("Pub", "Sub"))


def _documented(directions: tuple) -> set[str]:
    out = set()
    alt = "|".join(directions)
    pat = re.compile(rf"\|\s*(?:{alt})\s*\|\s*`/?([A-Za-z0-9_/]+)`")
    for line in FW_README.read_text().splitlines():
        if not line.lstrip().startswith("|"):
            continue
        m = pat.search(line)
        if m:
            out.add(m.group(1))
    return out


def test_sources_exist():
    assert MAIN_CPP.is_file(), f"firmware main.cpp not found at {MAIN_CPP}"
    assert FW_README.is_file(), f"firmware README not found at {FW_README}"


def test_parser_actually_finds_publishers():
    """Guard on the guard: a regex that matches nothing passes vacuously.

    The real check below is a set difference, and an empty left-hand side makes
    it trivially true -- which is exactly how a gate reports success while
    covering nothing. Pin a floor, and pin one topic known to be published.
    """
    pubs = _published_topics()
    assert len(pubs) >= 10, (
        f"only {len(pubs)} publishers parsed from main.cpp -- the regex has "
        f"probably drifted from the source. Found: {sorted(pubs)}"
    )
    assert "joint_states" in pubs, (
        "the parser did not find /joint_states, which main.cpp certainly "
        "publishes -- the regex is broken, not the firmware"
    )


def test_readme_actually_lists_topics():
    """Same guard for the other side of the comparison."""
    docs = _documented_topics()
    assert len(docs) >= 10, (
        f"only {len(docs)} Pub rows parsed from the firmware README -- the "
        f"table format has probably changed. Found: {sorted(docs)}"
    )


def test_every_published_topic_is_in_the_contract():
    missing = sorted(_published_topics() - _documented_topics() - set(UNDOCUMENTED_OK))
    assert not missing, (
        "main.cpp publishes topics that firmware/teensy/firmware/README.md does "
        f"not document: {missing}.\n\n"
        "This is not a paperwork complaint. dashcam/topics.py says in its "
        "docstring that it takes its names from that README; when a topic is "
        "missing there, downstream GUESSES, and a guessed topic name silently "
        "matches nothing. That is exactly how /servo_voltage and "
        "/servo_temperature came to be recorded by nothing while the dashcam "
        "waited on '/joint_voltages' and '/joint_temperatures'.\n\n"
        "Add a row to the contract table (Direction | Topic | Type | Rate | "
        "Notes), or add an entry to UNDOCUMENTED_OK with a real reason."
    )


def test_allow_list_entries_are_still_published():
    """A stale suppression is worse than none -- it hides a topic that left."""
    pubs = _published_topics()
    stale = sorted(t for t in UNDOCUMENTED_OK if t not in pubs)
    assert not stale, (
        f"UNDOCUMENTED_OK names topics main.cpp no longer publishes: {stale}. "
        "Remove them; a suppression outliving its subject silently widens the "
        "gate."
    )


@pytest.mark.parametrize("topic", ["servo_voltage", "servo_temperature"])
def test_the_two_that_caused_this(topic):
    """Regression pin for the specific pair, so the fix cannot silently revert."""
    assert topic in _published_topics(), f"{topic} is no longer published"
    assert topic in _documented_topics(), (
        f"{topic} dropped out of the firmware contract README -- this is the "
        "exact state that produced the dashcam name mismatch on 2026-08-10"
    )


# --- the other half of the seam ------------------------------------------------
# Publishers were the half that had already caused a bug, so they came first.
# Subscriptions are the higher-stakes direction: a host node publishing a name
# the firmware does not subscribe to means commands or SAFETY TABLES silently
# never arrive, and the firmware runs on its built-in defaults instead. Checked
# 2026-08-10 and the names DO match (tables_node.py publishes joint_limits /
# hfe_envelope / limp_pose exactly) -- this keeps it that way.


def test_parser_actually_finds_subscriptions():
    """Guard on the guard, same reasoning as the publisher floor."""
    subs = _subscribed_topics()
    assert len(subs) >= 4, (
        f"only {len(subs)} subscriptions parsed from main.cpp -- the regex has "
        f"probably drifted. Found: {sorted(subs)}"
    )
    assert "joint_commands" in subs, (
        "the parser did not find /joint_commands, which main.cpp certainly "
        "subscribes to -- the regex is broken, not the firmware"
    )


def test_every_subscribed_topic_is_in_the_contract():
    missing = sorted(_subscribed_topics() - _documented(("Sub",)))
    assert not missing, (
        "main.cpp SUBSCRIBES to topics the firmware README does not document: "
        f"{missing}.\n\n"
        "This direction is the more dangerous one. A publisher nobody reads "
        "loses telemetry; a subscription nobody publishes to loses COMMANDS or "
        "PROTECTION TABLES, and the firmware falls back to built-in defaults "
        "without saying so. Add a `| Sub |` row to the contract table."
    )


@pytest.mark.parametrize(
    "topic", ["joint_limits", "hfe_envelope", "limp_pose", "safety_clear"]
)
def test_protection_table_subscriptions_stay_documented(topic):
    """These three tables are how the host imposes limits on the firmware."""
    assert topic in _subscribed_topics(), f"{topic} is no longer subscribed"
    assert topic in _documented(("Sub",)), (
        f"{topic} dropped out of the contract table -- an undocumented safety "
        "table is how a host node comes to publish a name nothing receives"
    )


# --- payload SHAPE, not just presence -------------------------------------------
# The gate above proves a topic is documented. It does NOT prove the contract
# describes what the topic actually carries -- and on 2026-08-12 that gap had a
# live instance: /power_rails was documented as 9 floats while the firmware
# publishes 12. POWER_RAILS_FIELDS switches on NOVA_INA226_L2, that flag IS set in
# teensy_base.build_flags, and the 4th INA226 (L2 rail @0x45) was decided
# 2026-06-30 without the contract being updated. Nothing broke only because the
# single ROS consumer is length-defensive and reads index 0.
#
# This checks the ONE topic whose width is conditional. A general payload gate
# would need to model every message type; this models the thing that actually went
# wrong, which is a compile-time constant nobody re-read.

PIO_INI = REPO / "firmware/teensy/firmware/platformio.ini"


def _l2_flag_enabled() -> bool:
    return "-D NOVA_INA226_L2" in PIO_INI.read_text()


def _power_rails_fields() -> int:
    """POWER_RAILS_FIELDS as the ACTIVE build would see it."""
    src = MAIN_CPP.read_text()
    m = re.search(
        r"#ifdef\s+NOVA_INA226_L2\s*\n\s*constexpr\s+size_t\s+POWER_RAILS_FIELDS\s*=\s*(\d+)"
        r"\s*;\s*\n\s*#else\s*\n\s*constexpr\s+size_t\s+POWER_RAILS_FIELDS\s*=\s*(\d+)",
        src,
    )
    assert m, "POWER_RAILS_FIELDS #ifdef block not found -- main.cpp changed shape"
    return int(m.group(1) if _l2_flag_enabled() else m.group(2))


def test_power_rails_width_matches_the_contract():
    n = _power_rails_fields()
    row = [l for l in FW_README.read_text().splitlines() if "`/power_rails`" in l and "| Pub |" in l]
    assert row, "no /power_rails Pub row in the firmware contract"
    text = row[0]
    assert f"{n} floats" in text or f"**{n} floats**" in text, (
        f"the firmware publishes {n} floats on /power_rails (NOVA_INA226_L2 "
        f"{'set' if _l2_flag_enabled() else 'unset'}), but the contract row does not say "
        f"'{n} floats'.\n\nRow: {text[:200]}\n\n"
        "This is the failure that shipped on 2026-08-12: the row said 9 while the "
        "firmware sent 12, because the 4th INA226 (L2 @0x45) landed without the "
        "contract being updated. Anything sized from this table drops the L2 rail."
    )


def test_l2_rail_flag_and_field_count_agree():
    """The flag and the constant must not drift apart."""
    n = _power_rails_fields()
    assert n == (12 if _l2_flag_enabled() else 9), (
        f"POWER_RAILS_FIELDS resolved to {n} with the L2 flag "
        f"{'set' if _l2_flag_enabled() else 'unset'} -- expected 12/9. Either the rail "
        "count changed or the #ifdef was edited; re-read main.cpp before trusting either."
    )
