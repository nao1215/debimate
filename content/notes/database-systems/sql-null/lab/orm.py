"""SQLAlchemy で「誰も紹介していない会員」を 2 通りに書き、生成される SQL と件数を出す。

実行: pip install sqlalchemy のあと python3 orm.py（DB は SQLite のメモリ上）
"""
import sqlalchemy
from sqlalchemy import ForeignKey, create_engine, exists, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, aliased, mapped_column


class Base(DeclarativeBase):
    pass


class Member(Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    referred_by: Mapped[int | None] = mapped_column(ForeignKey("members.id"))


engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
with Session(engine) as s:
    s.add_all([
        Member(id=1, name="sato", referred_by=None),
        Member(id=2, name="suzuki", referred_by=1),
        Member(id=3, name="takahashi", referred_by=1),
        Member(id=4, name="tanaka", referred_by=None),
        Member(id=5, name="ito", referred_by=2),
    ])
    s.commit()

    # 書き方 1: 「紹介者の id の一覧に入っていない会員」
    q1 = select(Member.name).where(Member.id.not_in(select(Member.referred_by)))
    # 書き方 2: 「その会員を紹介者に持つ行が存在しない会員」
    r = aliased(Member)
    q2 = select(Member.name).where(~exists().where(r.referred_by == Member.id))

    print("sqlalchemy", sqlalchemy.__version__)
    for label, q in [("not_in", q1), ("not_exists", q2)]:
        print(f"-- {label}")
        print(q.compile(engine))
        print("=>", s.scalars(q).all())
