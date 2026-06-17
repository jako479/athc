# Source: https://github.com/python-openxml/python-docx/blob/master/features/doc-add-table.feature
# Why mimic: a real BDD Gherkin feature->scenario map. Each Scenario is ONE behavior/edge
# case in Given/When/Then form; the filename prefix (doc-, par-, run-, tbl-, txt-) groups
# features by component. This IS a feature->test mapping that doubles as living docs.
# (verbatim copy of the upstream file follows)

Feature: Add a table
  In order to include tablular information in a document
  As a developer using python-docx
  I need a way to add a table


  Scenario: Add a table specifying only row and column count
    Given a blank document
     When I add a 2 x 2 table specifying only row and column count
     Then the document contains a 2 x 2 table
      And table.style is styles['Normal Table']
      And the width of each column is 3.0 inches
      And the width of each cell is 3.0 inches


  Scenario: Add a table specifying style
    Given a document having built-in styles
     When I add a 2 x 2 table specifying style 'Table Grid'
     Then the document contains a 2 x 2 table
      And table.style is styles['Table Grid']
