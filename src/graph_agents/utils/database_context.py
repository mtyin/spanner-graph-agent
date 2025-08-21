# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field


class JsonField(BaseModel):
    key: str
    type: str


class JsonSchema(BaseModel):
    schema_object_name: str
    json_object_name: str
    json_fields: List[JsonField]


class Column(BaseModel):
    name: str
    type: str
    expr: Optional[str] = None


class Table(BaseModel):
    name: str
    key_columns: List[str]
    columns: List[Column]


class Index(BaseModel):
    name: str
    type: str
    table: Table
    columns: List[Column]
    filter: Optional[str]
    search_partition_by: Optional[List[str]]
    search_order_by: Optional[List[str]]


class PropertyDeclaration(BaseModel):
    name: str
    type: str


class Label(BaseModel):
    name: str
    property_declaration_names: Set[str]


class PropertyDefinition(BaseModel):
    name: str
    expr: str


class NodeReference(BaseModel):
    node_name: str


class GraphElement(BaseModel):
    name: str
    table_name: str
    key_column_names: List[str]
    label_names: List[str]
    property_definitions: Dict[str, PropertyDefinition]
    source_node_reference: Optional[NodeReference] = None
    dest_node_reference: Optional[NodeReference] = None


class PropertyGraph(BaseModel):
    name: str
    nodes: Dict[str, GraphElement]
    edges: Dict[str, GraphElement]
    labels: Dict[str, Label]
    property_declarations: Dict[str, PropertyDeclaration]

    def get_node_details(self, label: str):
        return NodeTypeDescriptor(
            type=label,
            properties=[
                {
                    "name": pname,
                    "type": self.property_declarations[pname].type,
                }
                for pname in self.labels[label.casefold()].property_declaration_names
            ],
        )

    def get_edge_details(self, label: str):
        triplet_labels = self.get_triplet_labels()
        return EdgeTypeDescriptor(
            type=label,
            properties=[
                {
                    "name": pname,
                    "type": self.property_declarations[pname].type,
                }
                for pname in self.labels[label].property_declaration_names
            ],
            related_edge_patterns=[
                f"(:{src_node_label})-[:{edge_label}]->(:{dst_node_label})"
                for src_node_label, edge_label, dst_node_label in triplet_labels
                if edge_label.casefold() == label.casefold()
            ],
        )

    def get_node_labels(self):
        return list(
            {label for node in self.nodes.values() for label in node.label_names}
        )

    def get_edge_labels(self):
        return list(
            {label for edge in self.edges.values() for label in edge.label_names}
        )

    def get_triplet_labels(self):
        node_labels = {name: node.label_names for name, node in self.nodes.items()}
        return list(
            {
                (src_node_label, edge_label, dst_node_label)
                for edge in self.edges.values()
                for edge_label in edge.label_names
                for src_node_label in node_labels[
                    edge.source_node_reference.node_name.casefold()
                ]
                for dst_node_label in node_labels[
                    edge.dest_node_reference.node_name.casefold()
                ]
            }
        )

    def get_label_and_properties(self, table_name: str):
        return [
            (
                lname,
                {
                    pdef.expr.casefold(): pdef.name
                    for pdef in element.property_definitions.values()
                    if pdef.name.casefold()
                    in self.labels[lname].property_declaration_names
                },
            )
            for element in itertools.chain(self.nodes.values(), self.edges.values())
            if element.table_name.casefold() == table_name.casefold()
            for lname in element.label_names
        ]

    def to_descriptor(self):
        return PropertyGraphDescriptor(
            name=self.name,
            nodes=[self.get_node_details(label) for label in self.get_node_labels()],
            edges=[self.get_edge_details(label) for label in self.get_edge_labels()],
        )


# PropertyGraphDescriptor is a readable representation for PropertyGraph that is
# used as context for LLM to do query generation.
#
# It consists mainly two differences comparing to PropertyGraph:
#
# - PropertyGraphDescriptor strips out information in PropertyGraph that isn't
#   necessary for query generation. For example, the base table names, node/edge
#   element table names. These information are not used during query time, hence
#   may confuse LLM.
#
# - PropertyGraphDescriptor represents the schema in a more intuitive way.
class NodeTypeDescriptor(BaseModel):
    type: str = Field(description="type of node")
    properties: List[Dict[str, str]] = Field(
        description="A list of node properties of the given node type"
    )


class EdgeTypeDescriptor(BaseModel):
    type: str = Field(description="type of edge")
    properties: List[Dict[str, str]] = Field(
        description="A list of node properties of the given node type"
    )
    related_edge_patterns: List[str] = Field(
        description="A list of possible edge patterns related to given edge type, in the form of (:SourceNodeType)-[:EdgeType]->(:TargetNodeType)."
    )


class PropertyGraphDescriptor(BaseModel):
    name: str = Field(description="Name of graph")
    nodes: List[NodeTypeDescriptor] = Field(description="List of node type descriptors")
    edges: List[EdgeTypeDescriptor] = Field(description="List of edge type descriptors")
