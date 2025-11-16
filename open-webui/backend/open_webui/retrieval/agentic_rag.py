"""
Agentic RAG + MCP Architecture Implementation

This module implements the Agentic RAG architecture with MCP (Model Context Protocol) integration.
The architecture follows this flow:
1. Analyze the query (possibly rewrite)
2. Determine if additional data is needed
3. If yes, LLM Agent interacts with MCP servers
4. Rerank search results
5. Generate answer
6. Analyze the answer for correctness/relevance
7. If not correct, rewrite query and loop back
"""

import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

log = logging.getLogger(__name__)


class QueryAnalysisResult:
    """Result of query analysis"""
    
    def __init__(
        self,
        needs_additional_data: bool,
        rewritten_query: Optional[str] = None,
        reasoning: Optional[str] = None,
        confidence: float = 1.0
    ):
        self.needs_additional_data = needs_additional_data
        self.rewritten_query = rewritten_query
        self.reasoning = reasoning
        self.confidence = confidence


class AnswerValidationResult:
    """Result of answer validation"""
    
    def __init__(
        self,
        is_correct: bool,
        is_relevant: bool,
        reasoning: Optional[str] = None,
        confidence: float = 1.0
    ):
        self.is_correct = is_correct
        self.is_relevant = is_relevant
        self.reasoning = reasoning
        self.confidence = confidence
        # Combined validation: answer is valid if both correct and relevant
        self.is_valid = is_correct and is_relevant


class AgenticRAGEngine:
    """
    Main Agentic RAG Engine that orchestrates the entire flow:
    - Query analysis and rewriting
    - MCP server interaction via LLM Agent
    - Search result reranking
    - Answer generation
    - Answer validation
    """
    
    def __init__(
        self,
        request,
        user,
        embedding_function,
        reranking_function=None,
        mcp_clients: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3
    ):
        self.request = request
        self.user = user
        self.embedding_function = embedding_function
        self.reranking_function = reranking_function
        self.mcp_clients = mcp_clients or {}
        self.max_iterations = max_iterations
        
    async def analyze_query(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None
    ) -> QueryAnalysisResult:
        """
        Step 1: Analyze the query and determine if additional data is needed.
        Optionally rewrite the query for better retrieval.
        """
        try:
            # Get task model for query analysis
            task_model_id = self._get_task_model_id()
            
            # Prepare messages for query analysis
            system_prompt = """You are a query analysis assistant. Your task is to:
1. Analyze the user's query to determine if additional data/documentation is needed to answer it
2. Optionally rewrite the query to improve retrieval if needed
3. Provide reasoning for your decision

Respond in JSON format:
{
    "needs_additional_data": true/false,
    "rewritten_query": "improved query or null",
    "reasoning": "explanation",
    "confidence": 0.0-1.0
}"""
            
            user_message = f"Query: {query}"
            if chat_history:
                recent_history = "\n".join([
                    f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}"
                    for msg in chat_history[-3:]
                ])
                user_message = f"Recent conversation:\n{recent_history}\n\n{user_message}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Call LLM for query analysis
            response = await self._call_llm(task_model_id, messages)
            
            # Parse response
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Extract JSON from response
            try:
                bracket_start = content.find("{")
                bracket_end = content.rfind("}") + 1
                if bracket_start != -1 and bracket_end != -1:
                    json_str = content[bracket_start:bracket_end]
                    result = json.loads(json_str)
                else:
                    # Fallback: try to infer from text
                    result = self._parse_analysis_from_text(content)
            except json.JSONDecodeError:
                result = self._parse_analysis_from_text(content)
            
            return QueryAnalysisResult(
                needs_additional_data=result.get("needs_additional_data", True),
                rewritten_query=result.get("rewritten_query") or query,
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.8)
            )
            
        except Exception as e:
            log.exception(f"Error analyzing query: {e}")
            # Default: assume we need additional data
            return QueryAnalysisResult(
                needs_additional_data=True,
                rewritten_query=query,
                reasoning=f"Error during analysis: {str(e)}",
                confidence=0.5
            )
    
    async def interact_with_mcp_servers(
        self,
        query: str,
        mcp_clients: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Step 2: LLM Agent interacts with MCP servers to gather additional data.
        Returns a list of results from MCP servers.
        """
        results = []
        
        if not mcp_clients:
            return results
        
        try:
            task_model_id = self._get_task_model_id()
            
            # Get available MCP tools
            available_tools = []
            for server_id, client in mcp_clients.items():
                try:
                    tool_specs = await client.list_tool_specs()
                    for tool_spec in tool_specs:
                        available_tools.append({
                            "server_id": server_id,
                            "tool_name": tool_spec.get("name"),
                            "description": tool_spec.get("description", ""),
                            "parameters": tool_spec.get("parameters", {})
                        })
                except Exception as e:
                    log.error(f"Error listing tools from MCP server {server_id}: {e}")
                    continue
            
            if not available_tools:
                return results
            
            # LLM Agent decides which tools to use
            system_prompt = f"""You are an AI agent that can interact with MCP (Model Context Protocol) servers.
Your task is to determine which tools to use to gather information for answering the user's query.

Available tools:
{json.dumps(available_tools, indent=2)}

Respond in JSON format:
{{
    "tools_to_use": [
        {{
            "server_id": "server_id",
            "tool_name": "tool_name",
            "arguments": {{"arg1": "value1"}}
        }}
    ],
    "reasoning": "explanation"
}}"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}"}
            ]
            
            response = await self._call_llm(task_model_id, messages)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse tool selection
            try:
                bracket_start = content.find("{")
                bracket_end = content.rfind("}") + 1
                if bracket_start != -1 and bracket_end != -1:
                    json_str = content[bracket_start:bracket_end]
                    tool_selection = json.loads(json_str)
                else:
                    return results
            except json.JSONDecodeError:
                return results
            
            # Execute selected tools
            tools_to_use = tool_selection.get("tools_to_use", [])
            for tool_info in tools_to_use:
                server_id = tool_info.get("server_id")
                tool_name = tool_info.get("tool_name")
                arguments = tool_info.get("arguments", {})
                
                if server_id in mcp_clients:
                    try:
                        client = mcp_clients[server_id]
                        result = await client.call_tool(tool_name, arguments)
                        results.append({
                            "server_id": server_id,
                            "tool_name": tool_name,
                            "result": result,
                            "query": query
                        })
                    except Exception as e:
                        log.error(f"Error calling MCP tool {server_id}/{tool_name}: {e}")
                        continue
                        
        except Exception as e:
            log.exception(f"Error interacting with MCP servers: {e}")
        
        return results
    
    async def rerank_search_results(
        self,
        search_results: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Step 3: Rerank search results using the reranking function.
        """
        if not self.reranking_function or not search_results:
            return search_results
        
        try:
            # Prepare sentences for reranking: (query, document) pairs
            sentences = []
            for result in search_results:
                if "document" in result:
                    for doc_text in result["document"]:
                        sentences.append((query, doc_text))
            
            if not sentences:
                return search_results
            
            # Call reranking function
            reranked_scores = self.reranking_function(sentences, user=self.user)
            
            # Apply reranking scores to results
            idx = 0
            for result in search_results:
                if "document" in result:
                    doc_scores = []
                    for _ in result["document"]:
                        if idx < len(reranked_scores):
                            doc_scores.append(reranked_scores[idx])
                            idx += 1
                        else:
                            doc_scores.append(0.0)
                    
                    # Sort documents by reranking score
                    if doc_scores:
                        sorted_pairs = sorted(
                            zip(result["document"], result.get("metadata", []), doc_scores),
                            key=lambda x: x[2],
                            reverse=True
                        )
                        result["document"] = [pair[0] for pair in sorted_pairs]
                        if "metadata" in result:
                            result["metadata"] = [pair[1] for pair in sorted_pairs]
            
            # Sort results by highest reranking score
            search_results.sort(
                key=lambda r: max([
                    score for score in [
                        s[2] for s in sorted(
                            zip(r.get("document", []), r.get("metadata", []), 
                                [0.0] * len(r.get("document", []))),
                            key=lambda x: x[2],
                            reverse=True
                        )
                    ]
                ]) if r.get("document") else 0.0,
                reverse=True
            )
            
        except Exception as e:
            log.exception(f"Error reranking search results: {e}")
        
        return search_results
    
    async def generate_answer(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[Dict]] = None,
        mcp_results: Optional[List[Dict]] = None
    ) -> str:
        """
        Step 4: Generate answer using LLM with context from RAG and MCP servers.
        """
        try:
            # Prepare context from RAG sources
            context_parts = [context] if context else []
            
            # Add MCP results to context
            if mcp_results:
                mcp_context = "\n\nAdditional information from external sources:\n"
                for mcp_result in mcp_results:
                    result_data = mcp_result.get("result", {})
                    if isinstance(result_data, list):
                        for item in result_data:
                            if isinstance(item, dict) and "text" in item:
                                mcp_context += f"- {item['text']}\n"
                            elif isinstance(item, str):
                                mcp_context += f"- {item}\n"
                    elif isinstance(result_data, dict):
                        mcp_context += f"- {json.dumps(result_data, indent=2)}\n"
                    elif isinstance(result_data, str):
                        mcp_context += f"- {result_data}\n"
                context_parts.append(mcp_context)
            
            full_context = "\n".join(context_parts)
            
            # Use the main model for answer generation
            model_id = self.request.app.state.config.MODEL if hasattr(
                self.request.app.state.config, "MODEL"
            ) else None
            
            if not model_id:
                # Fallback to task model
                model_id = self._get_task_model_id()
            
            # Prepare messages
            system_prompt = """You are a helpful assistant. Answer the user's question based on the provided context.
If the context doesn't contain enough information to answer the question, say so.
Cite sources when possible."""
            
            user_message = f"Context:\n{full_context}\n\nQuestion: {query}"
            
            messages = [{"role": "system", "content": system_prompt}]
            if chat_history:
                messages.extend(chat_history[-5:])  # Include recent history
            messages.append({"role": "user", "content": user_message})
            
            # Generate answer
            response = await self._call_llm(model_id, messages)
            answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return answer
            
        except Exception as e:
            log.exception(f"Error generating answer: {e}")
            return f"Error generating answer: {str(e)}"
    
    async def validate_answer(
        self,
        query: str,
        answer: str,
        chat_history: Optional[List[Dict]] = None
    ) -> AnswerValidationResult:
        """
        Step 5: Analyze the answer for correctness and relevance to the query.
        """
        try:
            task_model_id = self._get_task_model_id()
            
            system_prompt = """You are an answer validation assistant. Your task is to evaluate:
1. Is the answer correct (factually accurate and complete)?
2. Is the answer relevant to the query?

Respond in JSON format:
{
    "is_correct": true/false,
    "is_relevant": true/false,
    "reasoning": "explanation",
    "confidence": 0.0-1.0
}"""
            
            user_message = f"Query: {query}\n\nAnswer: {answer}"
            if chat_history:
                recent_history = "\n".join([
                    f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}"
                    for msg in chat_history[-2:]
                ])
                user_message = f"Recent conversation:\n{recent_history}\n\n{user_message}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await self._call_llm(task_model_id, messages)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse response
            try:
                bracket_start = content.find("{")
                bracket_end = content.rfind("}") + 1
                if bracket_start != -1 and bracket_end != -1:
                    json_str = content[bracket_start:bracket_end]
                    result = json.loads(json_str)
                else:
                    result = self._parse_validation_from_text(content)
            except json.JSONDecodeError:
                result = self._parse_validation_from_text(content)
            
            return AnswerValidationResult(
                is_correct=result.get("is_correct", True),
                is_relevant=result.get("is_relevant", True),
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.8)
            )
            
        except Exception as e:
            log.exception(f"Error validating answer: {e}")
            # Default: assume answer is valid
            return AnswerValidationResult(
                is_correct=True,
                is_relevant=True,
                reasoning=f"Error during validation: {str(e)}",
                confidence=0.5
            )
    
    async def rewrite_query(
        self,
        original_query: str,
        answer: str,
        validation_result: AnswerValidationResult,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Rewrite the query based on validation feedback.
        """
        try:
            task_model_id = self._get_task_model_id()
            
            system_prompt = """You are a query rewriting assistant. Your task is to rewrite the user's query
to improve retrieval and answer quality based on validation feedback.

Respond with only the rewritten query, no additional text."""
            
            user_message = f"""Original query: {original_query}
Generated answer: {answer}
Validation: {validation_result.reasoning}

Rewrite the query to get a better answer."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await self._call_llm(task_model_id, messages)
            rewritten = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return rewritten.strip() if rewritten else original_query
            
        except Exception as e:
            log.exception(f"Error rewriting query: {e}")
            return original_query
    
    async def process(
        self,
        query: str,
        collection_names: List[str],
        chat_history: Optional[List[Dict]] = None,
        k: int = 5,
        k_reranker: int = 3,
        r: float = 0.7
    ) -> Dict[str, Any]:
        """
        Main processing method that orchestrates the entire Agentic RAG flow.
        """
        current_query = query
        iteration = 0
        best_answer = None
        best_sources = []
        
        while iteration < self.max_iterations:
            iteration += 1
            log.info(f"Agentic RAG iteration {iteration}/{self.max_iterations}")
            
            # Step 1: Analyze query
            analysis = await self.analyze_query(current_query, chat_history)
            log.info(f"Query analysis: needs_data={analysis.needs_additional_data}, "
                    f"rewritten={analysis.rewritten_query != query}")
            
            # Use rewritten query if available
            if analysis.rewritten_query and analysis.rewritten_query != current_query:
                current_query = analysis.rewritten_query
                log.info(f"Using rewritten query: {current_query}")
            
            # Step 2: Interact with MCP servers if needed
            mcp_results = []
            if analysis.needs_additional_data and self.mcp_clients:
                mcp_results = await self.interact_with_mcp_servers(current_query, self.mcp_clients)
                log.info(f"Retrieved {len(mcp_results)} results from MCP servers")
            
            # Retrieve from vector database
            sources = []
            if analysis.needs_additional_data and collection_names:
                try:
                    from open_webui.retrieval.utils import query_collection_with_hybrid_search
                    
                    if self.request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
                        sources = query_collection_with_hybrid_search(
                            collection_names=collection_names,
                            queries=[current_query],
                            embedding_function=self.embedding_function,
                            k=k,
                            reranking_function=self.reranking_function,
                            k_reranker=k_reranker,
                            r=r,
                            hybrid_bm25_weight=self.request.app.state.config.HYBRID_BM25_WEIGHT,
                            user=self.user
                        )
                    else:
                        from open_webui.retrieval.utils import query_collection
                        sources = query_collection(
                            collection_names=collection_names,
                            queries=[current_query],
                            embedding_function=self.embedding_function,
                            k=k
                        )
                except Exception as e:
                    log.exception(f"Error querying collections: {e}")
            
            # Step 3: Rerank search results
            if sources and self.reranking_function:
                sources = await self.rerank_search_results(sources, current_query)
            
            # Prepare context from sources
            context = ""
            if sources:
                context_parts = []
                for source in sources[:k_reranker]:  # Use top k_reranker sources
                    if "document" in source:
                        for doc_text in source["document"][:2]:  # Limit documents per source
                            context_parts.append(doc_text)
                context = "\n\n".join(context_parts)
            
            # Step 4: Generate answer
            answer = await self.generate_answer(
                current_query,
                context,
                chat_history,
                mcp_results
            )
            
            # Step 5: Validate answer
            validation = await self.validate_answer(current_query, answer, chat_history)
            log.info(f"Answer validation: correct={validation.is_correct}, "
                    f"relevant={validation.is_relevant}, valid={validation.is_valid}")
            
            # If answer is valid, return it
            if validation.is_valid:
                best_answer = answer
                best_sources = sources
                break
            
            # If not valid and we have iterations left, rewrite query
            if iteration < self.max_iterations:
                current_query = await self.rewrite_query(
                    query,  # Use original query as base
                    answer,
                    validation,
                    chat_history
                )
                log.info(f"Rewriting query for next iteration: {current_query}")
            else:
                # Use the best answer we have
                best_answer = answer
                best_sources = sources
        
        # Return final result
        return {
            "answer": best_answer or "Unable to generate a satisfactory answer.",
            "sources": best_sources,
            "mcp_results": mcp_results if 'mcp_results' in locals() else [],
            "iterations": iteration,
            "final_query": current_query
        }
    
    def _get_task_model_id(self) -> str:
        """Get the task model ID for LLM calls"""
        from open_webui.utils.misc import get_task_model_id
        
        models = self.request.app.state.MODELS
        task_model_id = get_task_model_id(
            self.request.app.state.config.MODEL if hasattr(
                self.request.app.state.config, "MODEL"
            ) else None,
            self.request.app.state.config.TASK_MODEL,
            self.request.app.state.config.TASK_MODEL_EXTERNAL,
            models
        )
        return task_model_id
    
    async def _call_llm(self, model_id: str, messages: List[Dict]) -> Dict:
        """Call LLM with given messages"""
        from open_webui.utils.misc import generate_chat_completion
        
        form_data = {
            "model": model_id,
            "messages": messages,
            "stream": False
        }
        
        response = await generate_chat_completion(
            self.request,
            form_data,
            self.user,
            bypass_filter=True
        )
        
        return response
    
    def _parse_analysis_from_text(self, text: str) -> Dict:
        """Fallback parser for query analysis"""
        text_lower = text.lower()
        needs_data = any(word in text_lower for word in ["need", "require", "yes", "true"])
        return {
            "needs_additional_data": needs_data,
            "rewritten_query": None,
            "reasoning": text,
            "confidence": 0.6
        }
    
    def _parse_validation_from_text(self, text: str) -> Dict:
        """Fallback parser for answer validation"""
        text_lower = text.lower()
        is_correct = not any(word in text_lower for word in ["incorrect", "wrong", "false", "no"])
        is_relevant = not any(word in text_lower for word in ["irrelevant", "not relevant", "no"])
        return {
            "is_correct": is_correct,
            "is_relevant": is_relevant,
            "reasoning": text,
            "confidence": 0.6
        }

