from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db_setup import Category, Base

engine = create_engine('sqlite:///moviecategory.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

category1 = Category(name="action")

session.add(category1)
session.commit()

category2 = Category(name="fantasy")

session.add(category1)
session.commit()

category3 = Category(name="romance")

session.add(category1)
session.commit()

category4 = Category(name="horror")

session.add(category1)
session.commit()

category5 = Category(name="comedy")

session.add(category1)
session.commit()
