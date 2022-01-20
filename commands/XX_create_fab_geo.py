import components.repository as repo
import rhinoscriptsyntax as rs
from 01_create_panels import create_panels
from 02_create_beams import create_beams

def main():

    # create panels
    panels = create_panels()

    # create beams from panels
    beams = create_beams(panels)

if __name__ == "__main__":
    main()
