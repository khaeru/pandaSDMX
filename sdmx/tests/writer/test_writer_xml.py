import logging

import pytest

import sdmx
from sdmx.model import DataSet, DataStructureDefinition, Dimension, Key, Observation

log = logging.getLogger(__name__)


@pytest.fixture
def dsd():
    dsd = DataStructureDefinition()

    for order, id in enumerate(["FOO", "BAR", "BAZ"]):
        dsd.dimensions.append(Dimension(id=id, order=order))

    return dsd


@pytest.fixture
def obs(dsd):
    return Observation(dimension=dsd.make_key(Key, dict(FOO=1, BAR=2)), value=42.0)


def test_codelist(tmp_path, codelist):
    result = sdmx.to_xml(codelist, pretty_print=True)
    print(result.decode())


def test_ds(dsd, obs):
    # Write DataSet with Observations not in Series
    ds = DataSet(structured_by=dsd)
    ds.obs.append(obs)

    result = sdmx.to_xml(ds, pretty_print=True)
    print(result.decode())


def test_obs(obs):
    # Generate <gen:ObsKey> element for 2+-dimensional Observation.dimension
    exp = (
        '<gen:ObsKey><gen:Value id="FOO" value="1"/>'
        '<gen:Value id="BAR" value="2"/></gen:ObsKey>'
    )
    assert exp in sdmx.to_xml(obs).decode()


def test_structuremessage(tmp_path, structuremessage):
    result = sdmx.to_xml(structuremessage, pretty_print=True)
    print(result.decode())

    # Message can be round-tripped to/from file
    path = tmp_path / "output.xml"
    path.write_bytes(result)
    msg = sdmx.read_sdmx(path)

    # Contents match the original object
    assert (
        msg.codelist["CL_COLLECTION"]["A"].name["en"]
        == structuremessage.codelist["CL_COLLECTION"]["A"].name["en"]
    )

    # False because `structuremessage` lacks URNs, which are constructed automatically
    # by `to_xml`
    assert not msg.compare(structuremessage, strict=True)
    # Compares equal when allowing this difference
    assert msg.compare(structuremessage, strict=False)


_xf_ref = pytest.mark.xfail(
    raises=NotImplementedError, reason="Cannot write reference to .* without parent"
)
_xf_not_equal = pytest.mark.xfail(raises=AssertionError)


@pytest.mark.parametrize(
    "data_id, structure_id",
    [
        (
            "INSEE/CNA-2010-CONSO-SI-A17.xml",
            "INSEE/CNA-2010-CONSO-SI-A17-structure.xml",
        ),
        ("INSEE/IPI-2010-A21.xml", "INSEE/IPI-2010-A21-structure.xml"),
        ("ECB_EXR/1/M.USD.EUR.SP00.A.xml", "ECB_EXR/1/structure.xml"),
        ("ECB_EXR/ng-ts.xml", "ECB_EXR/ng-structure-full.xml"),
        # DSD reference does not round-trip correctly
        pytest.param(
            "ECB_EXR/rg-xs.xml",
            "ECB_EXR/rg-structure-full.xml",
            marks=pytest.mark.xfail(raises=RuntimeError),
        ),
        # Example of a not-implemented feature: DataSet with groups
        pytest.param(
            "ECB_EXR/sg-ts-gf.xml",
            "ECB_EXR/sg-structure-full.xml",
            marks=pytest.mark.xfail(raises=NotImplementedError),
        ),
    ],
)
def test_data_roundtrip(pytestconfig, specimen, data_id, structure_id, tmp_path):
    """Test that SDMX-ML DataMessages can be 'round-tripped'."""

    # Read structure from file
    with specimen(structure_id) as f:
        dsd = sdmx.read_sdmx(f).structure[0]

    # Read data from file, using the DSD
    with specimen(data_id) as f:
        msg0 = sdmx.read_sdmx(f, dsd=dsd)

    # Write to file
    path = tmp_path / "output.xml"
    path.write_bytes(sdmx.to_xml(msg0, pretty_print=True))

    # Read again, using the same DSD
    msg1 = sdmx.read_sdmx(path, dsd=dsd)

    # Contents are identical
    assert msg0.compare(msg1, strict=True), (
        path.read_text() if pytestconfig.getoption("verbose") else path
    )


@pytest.mark.parametrize(
    "specimen_id, strict",
    [
        ("ECB/orgscheme.xml", True),
        ("ECB_EXR/1/structure-full.xml", False),
        ("ESTAT/apro_mk_cola-structure.xml", True),
        pytest.param(
            "ISTAT/47_850-structure.xml", True, marks=[pytest.mark.skip(reason="Slow")]
        ),
        pytest.param("IMF/ECOFIN_DSD-structure.xml", True, marks=_xf_ref),
        ("INSEE/CNA-2010-CONSO-SI-A17-structure.xml", False),
        ("INSEE/IPI-2010-A21-structure.xml", False),
        pytest.param("INSEE/dataflow.xml", False, marks=_xf_not_equal),
        ("SGR/common-structure.xml", True),
        ("UNSD/codelist_partial.xml", True),
    ],
)
def test_structure_roundtrip(pytestconfig, specimen, specimen_id, strict, tmp_path):
    """Test that SDMX-ML StructureMessages can be 'round-tripped'."""

    # Read a specimen file
    with specimen(specimen_id) as f:
        msg0 = sdmx.read_sdmx(f)

    # Write to file
    path = tmp_path / "output.xml"
    path.write_bytes(sdmx.to_xml(msg0, pretty_print=True))

    # Read again
    msg1 = sdmx.read_sdmx(path)

    # Contents are identical
    assert msg0.compare(msg1, strict), (
        path.read_text() if pytestconfig.getoption("verbose") else path
    )
