# Copyright © 2022 Jean Michault
# Copyright © 2024 Gabriel Rios

# License: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# https://github.com/FamilySearch/gedcomx/blob/master/specifications/json-format-specification.md
# https://github.com/FamilySearch/gedcomx/blob/master/specifications/conceptual-model-specification.md
# https://www.familysearch.org/developers/docs/api/gx_json
# https://www.familysearch.org/developers/docs/api/fs_json
# https://github.com/FamilySearch/gedcomx-record/blob/master/specifications/record-specification.md
 
from collections import ChainMap

from .dateformal import DateFormal
from ._utilities import all_annotations, init_class

# gedcomx classes
class ExtensibleData:
  # Strange — “id” is not unique for all classes.
  # So we cannot index them all.
  # Some classes with unique “id”:
  #          Person, PlaceDescription, Relationship, SourceDescription, ChildAndParentsRelationship
  # Some classes with duplicate “id”:
  #          Fact, Name, Note, SourceReference
  # Example: KJC1-LMJ and KJZM-ZWN — their birth facts have the same “id”.
  # I suppose that in this case the id is unique relative to the parent object.
  # For example, a note for an individual has a unique identifier for that individual.

  _index = None
  id: str
  def __init__(self,id=None,tree=None):
    init_class(self)
    if id and self.__class__._index:
      self.__class__._index[id]=self
  def __new__(cls,id=None,tree=None):
    if id and cls._index and id in cls._index:
      return cls._index[id]
    else:
      return super(ExtensibleData, cls).__new__(cls)

class HasText:
  text: str
  def __init__(self):
    init_class(self)

class Link:
  href: str
  template: str
  title: str
  type: str
  accept: str
  allow: str
  hreflang: str
  count: int
  offset: int
  results: int
  def __init__(self):
    init_class(self)

class Qualifier:
  name: str
  value: str
  def __init__(self):
    init_class(self)

class HypermediaEnabledData(ExtensibleData):
  links: dict[str,Link]

class ResourceReference:
  resourceId: str
  resource: str
  def __init__(self):
    init_class(self)

class Attribution(ExtensibleData):
  contributor: ResourceReference
  modified: int
  changeMessage: str
  changeMessageResource: str
  creator: 	ResourceReference
  created: int

class Tag:
  resource: str
  conclusionId: str # familySearch !
  def __init__(self):
    init_class(self)

class OnlineAccount(ExtensibleData):
  serviceHomepage: ResourceReference
  accountName: str

class TextValue:
  lang: str
  value: str
  def __init__(self):
    init_class(self)
  def iseq(self,other):
    if isinstance(other,TextValue):
      return (self.lang == other.lang and self.value == other.value)
    return False

# https://www.familysearch.org/developers/docs/api/types/json_Agent
class Agent(HypermediaEnabledData):
  identifiers: dict[str, set]
  names: set[TextValue]
  homepage: ResourceReference
  openid: ResourceReference
  accounts: set[OnlineAccount]
  emails: set [ResourceReference]
  phones: set [ResourceReference]
  addresses: set [ResourceReference]
  person: ResourceReference

# https://www.familysearch.org/developers/docs/api/types/json_DiscussionReference
class DiscussionReference(HypermediaEnabledData):
  resourceId: str
  resource: str
  attribution: Attribution

# https://www.familysearch.org/developers/docs/api/types/json_SourceReference
class SourceReference(HypermediaEnabledData):
  description: str
  descriptionId: str
  attribution: Attribution
  qualifiers: set[Qualifier]
  # fs :
  tags: set[Tag]

class ReferencesSources:
  sources: set[SourceReference]
  def __init__(self):
    init_class(self)

class VocabElement:
  id: str
  uri: str
  subclass: str
  type: str
  sortName: str
  labels: set[TextValue]
  descriptions: set[TextValue]
  sublist: str
  position: int
  def __init__(self):
    init_class(self)

class VocabElementList:
  id: str
  title: str
  description: str
  uri: str
  elements: set[VocabElement]
  def __init__(self):
    init_class(self)

class FamilyView(HypermediaEnabledData):
  parent1: ResourceReference
  parent2: ResourceReference
  children: set[ResourceReference]

class Date(ExtensibleData):
  """
  " original: str
  " formal: DateFormal
  """
  original: str
  formal: DateFormal
  normalized: set[TextValue]
  confidence: str

  def __str__(self):
   if self.formal :
      return str(self.formal)
   elif self.original :
      return self.original
   else : return ''
    
class DisplayProperties(ExtensibleData):
  name: str
  gender: str
  lifespan: str
  birthDate: str
  birthPlace: str
  deathDate: str
  deathPlace: str
  marriageDate: str
  marriagePlace: str
  ascendancyNumber: str
  descendancyNumber: str
  relationshipDescription: str
  familiesAsParent: set[FamilyView]
  familiesAsChild: set[FamilyView]
  role: str

class Note(HypermediaEnabledData):
  subject: str
  text: str
  attribution: Attribution
  lang: str

class HasNotes:
  notes: set[Note]
  def __init__(self):
    init_class(self)

class Conclusion(HypermediaEnabledData):
  attribution: Attribution
  sources: set[SourceReference]
  analysis: ResourceReference
  notes: set[Note]
  lang: str
  confidence: str
  sortKey: str

class CitationField:
  def __init__(self):
    init_class(self)

class SourceCitation(TextValue,HypermediaEnabledData):
  citationTemplate: ResourceReference
  fields: set[CitationField]

class PlaceReference(ExtensibleData):
  original: str
  normalized: set[TextValue]
  description: str
  confidence: str
  latitude: float
  longitude: float
  names: set[TextValue]

class HasDateAndPlace:
  date: Date
  place: PlaceReference
  def __init__(self):
    init_class(self)

class Fact(Conclusion):
  date: Date
  place: PlaceReference
  value: str
  qualifiers: set[Qualifier]
  type: str
  id: str

class HasFacts:
  facts: set[Fact]
  def __init__(self):
    init_class(self)

class NamePart(ExtensibleData):
  type: str
  value: str
  qualifiers: set[Qualifier]

# FS : https://www.familysearch.org/developers/docs/api/types/json_NameFormInfo
class NameFormInfo:
  order: str

class NameForm(ExtensibleData):
  lang: str
  parts: set[NamePart]
  fullText: str
  nameFormInfo: set[NameFormInfo]
  def iseq(self,other):
    if isinstance(other,NameForm):
      return (self.lang == other.lang and self.fullText == other.fullText)
    return False

class Name(Conclusion):
  preferred: bool
  date: Date
  nameForms: set[NameForm]
  type: str

  def akSurname(self):
    """ akiri familian nomon
    """
    for nf in self.nameForms:
      for p in nf.parts :
        if p.type == 'http://gedcomx.org/Surname':
          return p.value
    return ''
  def akGiven(self):
    """ akiri la antaŭnomon
    """
    for nf in self.nameForms:
      for p in nf.parts :
        if p.type == 'http://gedcomx.org/Given':
          return p.value
    return ''

class EvidenceReference(HypermediaEnabledData):
  resource: str
  resourceId: str
  attribution: Attribution

class Subject(Conclusion):
  evidence: set[EvidenceReference]
  media: set[SourceReference]
  identifiers: dict[str,set]
  extracted: bool

class Gender(Conclusion):
  type: str

class PersonInfo:
  canUserEdit: bool
  privateSpaceRestricted: bool
  readOnly: bool
  visibleToAll: bool
  visibleToAllWhenUsingFamilySearchApps: bool  # (FS extension)
  def __init__(self):
    init_class(self)

class Relationship(Subject):
  _index: dict = dict()
  identifiers: dict[str,str]
  person1: ResourceReference
  person2: ResourceReference
  facts: set[Fact]
  type: str
  def postmaljsonigi(self,d):
  #  """ 
  #  """
    factsKunId = False
    factsSenId = False
    for f in self.facts :
      if f.id : factsKunId = True
      else : factsSenId = True
    if factsKunId and factsSenId :
      facts2=self.facts.copy()
      for f in self.facts :
        if not f.id : facts2.remove(f)
      self.facts=facts2
      
    if self.type == 'http://gedcomx.org/ParentChild' :
      if self.person2 and self.person2.resourceId in Person._index :
        child = Person._index[self.person2.resourceId]
        child._parents.add(self)
      if self.person1 and self.person1.resourceId in Person._index :
        parent = Person._index[self.person1.resourceId]
        parent._children.add(self)
    if self.type == 'http://gedcomx.org/Couple' :
      if self.person1 and self.person1.resourceId in Person._index :
        spouse = Person._index[self.person1.resourceId]
        spouse._spouses.add(self)
      if self.person2 and self.person2.resourceId in Person._index :
        spouse = Person._index[self.person2.resourceId]
        spouse._spouses.add(self)

# https://www.familysearch.org/developers/docs/api/types/json_ChildAndParentsRelationship
class ChildAndParentsRelationship(Subject):
  _index: dict = dict()
  parent1: ResourceReference
  parent2: ResourceReference
  child: ResourceReference
  parent1Facts: set[Fact]
  parent2Facts: set[Fact]
  def postmaljsonigi(self,d):
   if self.child and self.child.resourceId in Person._index :
     child = Person._index[self.child.resourceId]
     child._parentsCP.add(self)
   if self.parent1 and self.parent1.resourceId in Person._index :
     parent = Person._index[self.parent1.resourceId]
     parent._childrenCP.add(self)
   if self.parent2 and self.parent2.resourceId in Person._index :
     parent = Person._index[self.parent2.resourceId]
     parent._childrenCP.add(self)


class Value:
  lang: str
  type: str
  text: str


class Field:
  type: str
  values: set[Value]

class Person(Subject):
  _index: dict = dict()
  private: bool
  living: bool
  gender: Gender
  names: set[Name]
  facts: set[Fact]
  display: DisplayProperties
  personInfo: set[PersonInfo]
  discussion_references: set[DiscussionReference]
  fields: set[Field]
  sortKey: str  # NEW (FS extension)
  _parents: set[Relationship]
  _children: set[Relationship]
  _spouses: set[Relationship]
  _childrenCP: set[ChildAndParentsRelationship]
  _parentsCP: set[ChildAndParentsRelationship]
  def preferred_name(self):
    for n in self.names:
      if n.preferred: return n
    if len(self.names): return next(iter(self.names))
    return Name()

class Coverage(HypermediaEnabledData):
  spatial: PlaceReference
  temporal: Date

# familySearch extension
# https://www.familysearch.org/developers/docs/api/types/json_ArtifactMetadata
class artifactMetadata:
  filename: str
  qualifiers: set[Qualifier]
  width: int
  height: int
  size: int
  screeningState: str
  displayState: str
  editable: bool

class SourceDescription(Conclusion):
  _index: dict = dict()
  citations: set[SourceCitation]
  mediator: ResourceReference
  publisher: ResourceReference
  authors: set[str]
  componentOf: SourceReference
  titles: set[TextValue]
  identifiers: dict[str,set]
  rights: set[str]
  replacedBy: str
  replaces: set[str]
  statuses: set[str]
  about: str
  version: str
  resourceType: str
  mediaType: str
  coverage: set[Coverage]
  descriptions: set[TextValue]
  created: int
  modified: int
  published: int
  repository: Agent
  ### familySearch extension
  artifactMetadata: set[artifactMetadata]


class Address(ExtensibleData):
  city: str
  country: str
  postalCode: str
  stateOrProvince: str
  street: str
  street2: str
  street3: str
  street4: str
  street5: str
  street6: str
  value: str

class EventRole(Conclusion):
  person: str
  type: str

class Event(Subject):
  type: str
  date: Date
  place: PlaceReference
  roles: set[EventRole]

class Document(Conclusion):
  type: str
  extracted: bool
  textType: str
  text: str
  attribution: Attribution

class GroupRole(Conclusion):
  person: str
  type: str
  date: Date
  details: str

class Group(Subject):
  names: set[TextValue]
  date: Date
  place: PlaceReference
  roles: GroupRole

class PlaceDisplayProperties(ExtensibleData):
  name: str
  fullName: str
  type: str

# FS: https://www.familysearch.org/developers/docs/api/types/json_PlaceDescriptionInfo
class PlaceDescriptionInfo:
  zoomLevel: int
  relatedType: str
  relatedSubType: str

class PlaceDescription(Subject):
  _index: dict = dict()
  names: set[TextValue]
  temporalDescription: Date
  latitude: float
  longitude: float
  spatialDescription: ResourceReference
  place: ResourceReference
  jurisdiction: ResourceReference
  display: PlaceDisplayProperties
  type: str
  placeDescriptionInfo: set[PlaceDescriptionInfo] # family search ! 

class Gender(Conclusion):
  type: str

class Gedcomx(HypermediaEnabledData):
  # https://github.com/FamilySearch/gedcomx/blob/master/specifications/xml-format-specification.md#gedcomx-type
  etag: str
  last_modified: int
  attribution: Attribution
  persons: set[Person]
  relationships: set[Relationship]
  sourceDescriptions: set[SourceDescription]
  agents: set[Agent]
  events: set[Event]
  places: set[PlaceDescription]
  documents: set[Document]
  groups: set[Group]
  lang: str
  description: str  # URI must resolve to SourceDescription
  notes: Note
  childAndParentsRelationships: set[ChildAndParentsRelationship]
  sourceReferences: set[SourceReference]
  genders: set[Gender]
  names: set[Name]
  facts: set[Fact]
  # Accept FS wrappers & metadata (e.g., { "person": {"persons":[…]}, "etag": "...", "last_modified": … })
  def deserialize_json(self, data):
    # Copy top-level meta if present
    if isinstance(data, dict):
      if "etag" in data:
        self.etag = data["etag"]
      if "last_modified" in data:
        self.last_modified = data["last_modified"]

      # Unwrap common FS wrapper: { "person": { "persons": [...] } }
      if "person" in data and isinstance(data["person"], dict):
        # Merge inner items up into the same dict the generic mapper will consume
        # without clobbering already-present root keys.
        unwrapped = {**data, **{k: v for k, v in data["person"].items()}}
        # Remove the wrapper key to avoid unknown-field warnings
        unwrapped.pop("person", None)
        data = unwrapped

    # Hand off to the generic mapper in required/raw mode to avoid recursion
    from .json import deserialize_json as _dj
    _dj(self, data, required=True)