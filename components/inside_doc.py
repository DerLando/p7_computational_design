import rhinoinside
rhinoinside.load()

import Rhino

doc = Rhino.RhinoDoc.CreateHeadless(None)
Rhino.RhinoDoc.ActiveDoc = doc