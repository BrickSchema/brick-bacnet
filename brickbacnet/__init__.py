from bacpypes.basetypes import PropertyIdentifier
from bacpypes.object import Object, OptionalProperty
from bacpypes.primitivedata import CharacterString

PropertyIdentifier.enumerations['jciName'] = 2390
Object.properties.append(OptionalProperty('jciName', CharacterString))
