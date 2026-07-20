param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
)

$ErrorActionPreference = 'Stop'

$governanceDirectory = Join-Path $RepositoryRoot 'docs\governance'
$biblePath = Join-Path $governanceDirectory 'PeerSlate_Company_and_Product_Bible_v2.6.docx'
$roadmapPath = Join-Path $governanceDirectory 'PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx'

function Get-ParagraphByText {
    param(
        [Parameter(Mandatory)]$Document,
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string]$StyleName
    )

    $matches = @()
    foreach ($paragraph in $Document.Paragraphs) {
        $paragraphText = $paragraph.Range.Text.Trim([char]13, [char]7)
        if ($paragraphText -eq $Text -and $paragraph.Style.NameLocal -eq $StyleName) {
            $matches += $paragraph
        }
    }
    if ($matches.Count -ne 1) {
        throw "Expected one '$StyleName' paragraph '$Text'; found $($matches.Count)."
    }
    return $matches[0]
}

function Set-TableLandscapeSection {
    param(
        [Parameter(Mandatory)]$Document,
        [Parameter(Mandatory)][int]$TableIndex,
        [Parameter(Mandatory)][string]$ExpectedHeader,
        [Parameter(Mandatory)][string]$HeadingText,
        [Parameter(Mandatory)][string]$HeadingStyle
    )

    $table = $Document.Tables.Item($TableIndex)
    $actualHeader = $table.Cell(1, 1).Range.Text.Trim([char]13, [char]7)
    if ($actualHeader -ne $ExpectedHeader) {
        throw "Table $TableIndex has header '$actualHeader'; expected '$ExpectedHeader'."
    }

    $afterTable = $table.Range.Duplicate
    $afterTable.Collapse(0)
    $afterTable.InsertBreak(2)

    $heading = Get-ParagraphByText `
        -Document $Document `
        -Text $HeadingText `
        -StyleName $HeadingStyle
    $beforeHeading = $heading.Range.Duplicate
    $beforeHeading.Collapse(1)
    $beforeHeading.InsertBreak(2)

    $table.Range.Sections.Item(1).PageSetup.Orientation = 1
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$word.Options.BackgroundSave = $false

try {
    $bible = $word.Documents.Open($biblePath, $false, $false)
    try {
        $bible.Repaginate()
        foreach ($tableOfContents in $bible.TablesOfContents) {
            $tableOfContents.Update()
            $tableOfContents.UpdatePageNumbers()
        }
        $bible.Repaginate()
        foreach ($tableOfContents in $bible.TablesOfContents) {
            $tableOfContents.UpdatePageNumbers()
        }
        $bible.Save()
        Write-Output ("Finalized Bible: {0} pages" -f $bible.ComputeStatistics(2))
    }
    finally {
        $bible.Close($false)
    }

    $roadmap = $word.Documents.Open($roadmapPath, $false, $false)
    try {
        if ($roadmap.Tables.Count -ne 115) {
            throw "Expected 115 Roadmap tables; found $($roadmap.Tables.Count)."
        }

        Set-TableLandscapeSection `
            -Document $roadmap `
            -TableIndex 107 `
            -ExpectedHeader 'Order' `
            -HeadingText 'First decision package' `
            -HeadingStyle 'Heading 2'
        Set-TableLandscapeSection `
            -Document $roadmap `
            -TableIndex 102 `
            -ExpectedHeader 'Package ID' `
            -HeadingText '18. Work-package register' `
            -HeadingStyle 'Heading 1'

        $roadmap.Repaginate()
        foreach ($tableOfContents in $roadmap.TablesOfContents) {
            $tableOfContents.Update()
            $tableOfContents.UpdatePageNumbers()
        }
        $roadmap.Repaginate()
        foreach ($tableOfContents in $roadmap.TablesOfContents) {
            $tableOfContents.UpdatePageNumbers()
        }
        if ($roadmap.Sections.Count -ne 5) {
            throw "Expected five Roadmap sections after landscape layout; found $($roadmap.Sections.Count)."
        }
        $roadmap.Save()
        Write-Output ("Finalized Roadmap: {0} pages across {1} sections" -f $roadmap.ComputeStatistics(2), $roadmap.Sections.Count)
    }
    finally {
        $roadmap.Close($false)
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
