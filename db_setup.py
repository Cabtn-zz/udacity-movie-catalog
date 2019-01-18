import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    image = Column(String(250))
    provider = Column(String(25))


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)


class Movie(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    director = Column(String(250), nullable=False)
    category = relationship(Category)
    category_name = Column(String(250))
    cateogory_id = Column(Integer, ForeignKey('category.id'))
    email = Column(String(250), nullable=False)


engine = create_engine('sqlite:///moviecategory.db')
Base.metadata.create_all(engine)
