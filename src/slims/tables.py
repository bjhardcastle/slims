import datetime
import hashlib
import pathlib
from collections.abc import Sequence
from typing import Literal, Optional
import sqlite3

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Uuid, Enum, Integer, String, Table
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from sqlalchemy import create_engine

DB_PATH = pathlib.Path("test.db")
DB_PATH.unlink(missing_ok=True)
sqlite3.connect(DB_PATH).close()
DB = f"sqlite:///{DB_PATH}"
engine = create_engine(DB, echo=True)

class Base(DeclarativeBase):
    pass


class LIMSEcephysSession(Base):
    
    __tablename__ = "lims_ecephys_sessions"
    
    lims_id: Mapped[int] = mapped_column(primary_key=True)
    
    recording = relationship("Recording", back_populates="lims_session", uselist=False)
    
    @property
    def probes(self) -> Sequence['Probe']:
        return [probe for probe in self.recording.probes]
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.lims_id!r})"
    
    @classmethod
    def dummy(cls) -> 'LIMSEcephysSession':
        return cls(lims_id=12345678)
    
class Recording(Base):
    __tablename__ = "recordings"
    
    settings_xml_md5: Mapped[str] = mapped_column(primary_key=True)
    lims_session_id: Mapped[Optional['LIMSEcephysSession']] = mapped_column(ForeignKey("lims_ecephys_sessions.lims_id"), nullable=True)
    hostname: Mapped[str]
    rig: Mapped[Optional[str]]
    date: Mapped[datetime.date]
    start_time: Mapped[datetime.time]
    duration: Mapped[Optional[datetime.timedelta]] # May be able to compute from .npx2 mtime
    open_ephys_version: Mapped[str]
    
    probes = relationship("ProbeRecording", back_populates="recording")
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
    
class Probe(Base):
    __tablename__ = "probes"
    
    NeuropixelsVersion = Enum('1.0', 'Ultra', name='neuropixels_version_enum')
    
    serial_number: Mapped[int] = mapped_column(primary_key=True)
    neuropixels_version = mapped_column(NeuropixelsVersion, nullable=True)
    
    recordings = relationship("ProbeRecording", back_populates="probe")
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.serial_number!r})"

    @classmethod
    def dummy(cls) -> 'Probe':
        return cls(serial_number=18005117142, neuropixels_version='1.0')
        
class ProbeRecording(Base):
    """A recording on a specific probe.
    
    Establishes many-to-many relationship between probes and recordings."""
    __tablename__ = "probe_recordings"
    
    ProbeLetterEnum = Enum('A', 'B', 'C', 'D', 'E', 'F', name='probe_letter_enum')
    
    settings_xml_md5: Mapped[str] = mapped_column(ForeignKey('recordings.settings_xml_md5'), primary_key=True)
    probe_serial_number: Mapped[int] = mapped_column(ForeignKey('probes.serial_number'), primary_key=True)
    probe_letter: Mapped[str] = mapped_column(ProbeLetterEnum)
    
    recording = relationship("Recording", back_populates="probes")
    probe = relationship("Probe", back_populates="recordings")
    
    @classmethod
    def dummy(cls) -> 'ProbeRecording':
        return cls(settings_xml_md5=Recording.dummy().settings_xml_md5, probe_serial_number=Probe.dummy().serial_number, probe_letter='A')

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.recording.rig or self.recording.hostname}_{self.recording.lims_session_id or '-no-lims-id'}_{self.recording.date:%Y%m%d}_probe{self.probe_letter})"
        

Base.metadata.create_all(engine)

from sqlalchemy.orm import Session

with Session(engine) as session:
    # probe = Probe(serial_number=18005117142)
    session.merge(Recording.dummy())
    session.merge(Probe.dummy())
    session.add(ProbeRecording.dummy())
    session.add(LIMSEcephysSession.dummy())
    session.commit()

from sqlalchemy import select

session = Session(engine)

stmt = select(Probe).where(Probe.serial_number.in_([18005117142]))

for probe in session.scalars(stmt):
    print(probe)
    
import pandas as pd
df = pd.read_sql_table('lims_ecephys_sessions', engine)