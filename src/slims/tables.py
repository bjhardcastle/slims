from __future__ import annotations

import contextlib
import csv
import datetime
import enum
import hashlib
import pathlib
import sqlite3
from collections.abc import Sequence
from typing import ClassVar, Optional

from typing_extensions import Literal
import uuid
import np_config
import numpy as np

from sqlalchemy import (Column, Enum, ForeignKey, Identity, Integer, String, Table, Uuid,
                        create_engine, select)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
import pandas as pd

# ------------------------------------------------------------------------------------
# allow integers >8 bytes to be stored in sqlite3
sqlite3.register_adapter(np.int64, lambda val: int(val))
sqlite3.register_adapter(np.int32, lambda val: int(val))
# ------------------------------------------------------------------------------------

DB_PATH = pathlib.Path("test.db")
# with contextlib.suppress(OSError):
#     DB_PATH.unlink()
sqlite3.connect(DB_PATH).close()
DB = f"sqlite:///{DB_PATH}"
ENGINE = create_engine(DB, echo=False)


class Base(DeclarativeBase):
    pass

class MultiSessionRecording(Base):
    # week_start_date
    pass

class Mouse(Base):
    # implant
    pass


    
class LIMSEcephysSession(Base):
    
    __tablename__ = "lims_ecephys_sessions"
    
    lims_id: Mapped[int] = mapped_column(primary_key=True)
    folder: Mapped[str]
    recording = relationship("Recording", back_populates="lims_session", uselist=False)
    
    @property
    def sorted_probe_recordings(self) -> tuple['SortedProbeRecording', ...]:
        return tuple(probe for probe in self.recording.sorted_probe_recordings)
    
    @property
    def neuropixels_probes(self) -> tuple['NeuropixelsProbe', ...]:
        return tuple(probe for probe in self.recording.neuropixels_probes)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.lims_id!r})"
    
    @classmethod
    def dummy(cls) -> 'LIMSEcephysSession':
        return cls(lims_id=12345678)
    
class Recording(Base):
    """
    A recording in OpenEphys with one or more probes and metadata in a settings.xml file. 
    """
    __tablename__ = "recordings"
    
    settings_xml_md5: Mapped[str] = mapped_column(primary_key=True)
    lims_session_id: Mapped[Optional['LIMSEcephysSession']] = mapped_column(ForeignKey("lims_ecephys_sessions.lims_id"), nullable=True)
    hostname: Mapped[str]
    rig: Mapped[Optional[str]]
    date: Mapped[datetime.date]
    start_time: Mapped[datetime.time]
    duration: Mapped[Optional[datetime.timedelta]] # May be able to compute from .npx2 st_mtime
    open_ephys_version: Mapped[str]
    
    sorted_probe_recordings = relationship("SortedProbeRecording", back_populates="recording")
    lims_session = relationship("LIMSEcephysSession", back_populates="recording")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.settings_xml_md5!r})"
    
    @classmethod
    def dummy(cls) -> 'Recording':
        return cls(
            settings_xml_md5=hashlib.md5(b'dummy').hexdigest(),
            lims_session_id=LIMSEcephysSession.dummy().lims_id,
            hostname='localhost',
            rig='NP.1',
            date=datetime.date(2021, 1, 1),
            start_time=datetime.time(12, 0, 0),
            open_ephys_version='0.4.1',
            )
    
class NeuropixelsProbe(Base):
    """
    Represents a Neuropixels probe tracked by its serial number.
    """
    __tablename__ = "neuropixels_probes"
    
    serial_number: Mapped[int] = mapped_column(primary_key=True)
    
    # class NeuropixelsVersion(enum.Enum):
    #     unknown = 'unknown'
    #     np_3a = '3a'
    #     np_1_0 = '1.0'
    #     np_ultra = 'Ultra'
    # NeuropixelsVersionDB =  Enum(NeuropixelsVersion, name='neuropixels_version_enum', nullable=True)
    # NeuropixelsVersionDB.values_callable = lambda x: [e.value for e in x]
    NeuropixelsVersion = Enum('unknown', '3a', '1.0', 'Ultra', name='neuropixels_version_enum', nullable=True)
    neuropixels_version = mapped_column(NeuropixelsVersion, nullable=True)

    # recordings = relationship("Recording", back_populates="neuropixels_probes")
    sorted_probe_recordings = relationship("SortedProbeRecording", back_populates="neuropixels_probe")
    # sorted_units = relationship("SortedUnit", back_populates="neuropixels_probe")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.serial_number!r})"

    @classmethod
    def dummy(cls) -> 'NeuropixelsProbe':
        return cls(serial_number=18005117142, neuropixels_version='1.0')
    
class SortedUnit(Base):
    """
    An individual unit recorded on a probe, with summary statistics in a
    metrics.csv file.
    """
    __tablename__ = "sorted_units"
    
    id = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metrics_csv_md5: Mapped[str]
    metrics_csv_path: Mapped[str]
    
    @property
    def metrics_csv(self) -> pathlib.Path:
        return pathlib.Path(self.metrics_csv_path)
    
    sorted_probe_recording = relationship("SortedProbeRecording", back_populates="sorted_units", uselist=False)
    # neuropixels_probe = relationship("NeuropixelsProbe", back_populates="sorted_units")
    
    cluster_id: Mapped[int]
    firing_rate: Mapped[Optional[float]]
    presence_ratio: Mapped[Optional[float]]
    isi_viol: Mapped[Optional[float]]	
    amplitude_cutoff: Mapped[Optional[float]]
    isolation_distance: Mapped[Optional[float]]
    l_ratio: Mapped[Optional[float]]
    d_prime: Mapped[Optional[float]]
    nn_hit_rate: Mapped[Optional[float]]
    nn_miss_rate: Mapped[Optional[float]]
    silhouette_score: Mapped[Optional[float]]
    max_drift: Mapped[Optional[float]]
    cumulative_drift: Mapped[Optional[float]]
    epoch_name_quality_metrics: Mapped[Optional[str]]
    epoch_name_waveform_metrics: Mapped[Optional[str]]
    peak_channel: Mapped[Optional[int]]
    snr: Mapped[Optional[float]]
    duration: Mapped[Optional[float]]
    halfwidth: Mapped[Optional[float]]
    PT_ratio: Mapped[Optional[float]]
    repolarization_slope: Mapped[Optional[float]]
    recovery_slope: Mapped[Optional[float]]
    amplitude: Mapped[Optional[float]]
    spread: Mapped[Optional[int]]
    velocity_above: Mapped[Optional[float]]
    velocity_below: Mapped[Optional[float]]
    quality = mapped_column(Enum('good', 'noise', name='quality_enum'), nullable=True)
    
    @classmethod
    def from_csv_path(cls, csv_path: pathlib.Path) -> tuple['SortedUnit', ...]:
        csv_path = pathlib.Path(csv_path)
        metrics_csv_md5 = md5(csv_path)
        df = pd.read_csv(csv_path, index_col=0)
        df = df.replace({np.nan:None})
        # reader = csv.DictReader(csv_path.read_text(), cls.fieldnames)
        return tuple(
            cls(
                metrics_csv_md5=metrics_csv_md5,
                metrics_csv_path=np_config.normalize_path(csv_path).as_posix(),
                **{
                    metric: df.loc[idx][metric]
                    for metric in df.columns
                },
            )         
            for idx in df.index
        )
        
    @classmethod
    def dummy(cls) -> SortedUnit:
        return cls.from_csv_path(
            r'\\allen\programs\mindscope\workgroups\np-ultra\0_0_20230123\0_0_20230123_probeF_sorted\continuous\Neuropix-PXI-100.0\metrics.csv'
        )[0]

class CommonCoordinateFrameworkProbeLocalizations(Base):
    
    metrics_csv_md5: Mapped[int] = mapped_column(ForeignKey('sorted_units.metrics_csv_md5'), primary_key=True)
    channel: Mapped[int]
    x: Mapped[float]
    y: Mapped[float]
    z: Mapped[float]

class SortedProbeRecording(Base):
    """Represents a recording on a specific probe with a `metrics.csv` file.
    
    Establishes many-to-many relationship between probes and recordings.
    """
    
    __tablename__ = "sorted_probe_recordings"
    
    ProbeLetterEnum = Enum('A', 'B', 'C', 'D', 'E', 'F', name='probe_letter_enum')
    
    settings_xml_md5: Mapped[str] = mapped_column(ForeignKey('recordings.settings_xml_md5'), primary_key=True)
    probe_serial_number: Mapped[int] = mapped_column(ForeignKey('neuropixels_probes.serial_number'), primary_key=True)
    metrics_csv_md5: Mapped[str] = mapped_column(ForeignKey('sorted_units.metrics_csv_md5'), primary_key=True)
    
    probe_letter: Mapped[Optional[str]] = mapped_column(ProbeLetterEnum)
    
    implant: Mapped[Optional[str]]
    implant_hole: Mapped[Optional[str]]
    
    recording = relationship("Recording", back_populates="sorted_probe_recordings", uselist=False)
    neuropixels_probe = relationship("NeuropixelsProbe", back_populates="sorted_probe_recordings", uselist=False)
    sorted_units = relationship("SortedUnit", back_populates="sorted_probe_recording")
    
    @classmethod
    def dummy(cls) -> 'SortedProbeRecording':
        return cls(
            settings_xml_md5=Recording.dummy().settings_xml_md5, 
            probe_serial_number=NeuropixelsProbe.dummy().serial_number, 
            probe_letter='A',
            metrics_csv_md5=SortedUnit.dummy().metrics_csv_md5, 
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.recording.rig or self.recording.hostname}_{self.recording.lims_session_id or '-no-lims-id'}_{self.recording.date:%Y%m%d}_probe{self.probe_letter})"

def md5(path: str | pathlib.Path) -> str:
    return hashlib.md5(pathlib.Path(path).read_bytes()).hexdigest()

Base.metadata.create_all(ENGINE)
SESSION = Session(ENGINE)

if __name__ == "__main__":


    # with SESSION as session:
    #     # probe = NeuropixelsProbe(serial_number=18005117142)
    #     session.merge(Recording.dummy())
    #     session.merge(NeuropixelsProbe.dummy())
    #     session.add(SortedProbeRecording.dummy())
    #     session.add(LIMSEcephysSession.dummy())
    #     session.add_all(
    #         SortedUnit.from_csv_path(r'\\allen\programs\mindscope\workgroups\np-ultra\0_0_20230123\0_0_20230123_probeF_sorted\continuous\Neuropix-PXI-100.0\metrics.csv')
    #     )
    #     session.commit()


    # stmt = select(NeuropixelsProbe).where(NeuropixelsProbe.serial_number.in_([18005117142]))

    # for probe in SESSION.scalars(stmt):
    #     print(probe)
        
    
    tuple(SESSION.scalars(select(LIMSEcephysSession).where(NeuropixelsProbe.serial_number.in_([18005117142]))))
    tuple(SESSION.scalars(select(SortedUnit).outerjoin(SortedProbeRecording)))
    
    # requires pandas ver that doesn't support 3.7
    df = pd.read_sql_table('sorted_units', DB, schema=None)
